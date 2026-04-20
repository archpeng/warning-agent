# warning-agent W6 Feishu delivery bridge contract

- status: `planning-support / queued-slice-prep`
- owner: `W6.S2a` + `W6.S2b`
- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- followup_design: `docs/plan/warning-agent-production-integration-bridge-2026-04-20_S2A_FEISHU_CODE_DESIGN.md`
- last_updated: `2026-04-20`

## 1. Decision summary

W6 wave-2 的首个 live vendor adapter 固定为：`adapter-feishu`。

本次只支持并只诚实声称下面这条路径：

```text
warning-agent -> adapter-feishu -> Feishu/Lark
```

当前明确不做、也不得在 W6.S2a/S2b 内偷渡成已支持的路径：

```text
alert -> adapter-feishu -> warning-agent submit/report orchestration -> Feishu
```

原因：`adapter-feishu` 当前已明确把上面第二条路径标记为 blocked；它依赖 `warning-agent` 未来提供稳定 external alert/report API，而这不属于当前 W6 wave-2 的 honest scope。

## 2. Audited interface truth

### 2.1 warning-agent side

审计输入：

- `app/reports/contracts.py`
- `app/reports/markdown_builder.py`
- `app/runtime_entry.py`
- `app/delivery/runtime.py`
- `configs/delivery.yaml`
- `tests/test_delivery.py`
- `tests/test_runtime_entry.py`
- `tests/test_alertmanager_webhook.py`

当前 repo truth：

1. `warning-agent` 当前会 materialize `alert-report.v1` report artifact，并把完整 Markdown 落到 `report_record["markdown"]`。
2. 当前 delivery plane 只有 durable local adapters：
   - `markdown_only`
   - `local_ticket_queue`
   - `local_page_queue`
   - `local_review_queue`
3. 当前 `configs/delivery.yaml` 还没有 live vendor seam。
4. 当前 runtime / webhook path 都会调用同一 delivery runtime；因此 wave-2 改动必须同时覆盖 replay/runtime 和 webhook path。
5. 当前 report/frontmatter truth 已足够生成一个 provider notification payload，不要求先新增 report polling API。

### 2.2 adapter-feishu side

审计输入（sibling repo audit at planning time）：

- `adapter-feishu/docs/runbook/adapter-feishu-provider-integration.md`
- `adapter-feishu/docs/architecture/adapter-feishu-architecture.md`
- `adapter-feishu/src/core/contracts.ts`
- `adapter-feishu/src/providers/warning-agent/contracts.ts`
- `adapter-feishu/src/providers/warning-agent/normalize.ts`
- `adapter-feishu/src/server/providerWebhook.ts`
- `adapter-feishu/src/runtime.ts`
- `adapter-feishu/src/channels/feishu/replySink.ts`
- `adapter-feishu/test/server/providerWebhook.test.ts`
- `adapter-feishu/test/providers/warning-agent/index.test.ts`

当前 repo truth：

1. `adapter-feishu` 已支持 notify-first provider push：`POST /providers/webhook`。
2. `warning-agent` provider 当前接受的最小 payload 是 `WarningAgentNotificationPayload`，必填字段只有：
   - `reportId`
   - `runId`
   - `summary`
3. 对当前真实 runtime 来说，`target` 应视为 **required**：
   - 文档允许“未来 runtime 注入 defaultTarget”
   - 但当前 `createAdapterRuntime(...)` 在 provider webhook path 中并未注入 `defaultTarget`
   - `replySink` 最终要求 `target` 存在，且 Feishu target 必须至少给出 `chatId` 或 `openId`
4. `adapter-feishu` 当前 provider webhook response 是：
   - HTTP `202`
   - JSON body 至少包含：`code`, `providerKey`, `status`
5. `adapter-feishu` 当前 dedupe key 规则：
   - 优先 `incidentId`
   - 否则回退到 `reportId`
6. `adapter-feishu` 当前 scope 只要求它把 provider notification 渲染成 Feishu message/card；不要求它拥有 `warning-agent` 的 diagnosis truth、长期 report storage 或 alert-forward orchestration。

## 3. Chosen minimal bridge contract

### 3.1 Transport

`warning-agent` live delivery client for Feishu bridge:

- method: `POST`
- url: `${WARNING_AGENT_ADAPTER_FEISHU_BASE_URL}/providers/webhook`
- content-type: `application/json`
- timeout: bounded local timeout, default `5s`
- success envelope:
  - HTTP `202`
  - JSON `code = 0`
  - JSON `status in {"delivered", "duplicate_ignored"}`
- fail-closed cases:
  - missing base URL env
  - missing target env
  - network error / timeout
  - non-`202` status
  - invalid JSON response
  - `code != 0`
  - provider `status` not in accepted set

W6 honest rule：

- env missing -> `deferred` / `rejected`，且 **不得发起 HTTP request**
- request fired but failed -> `failed`
- only accepted adapter response -> `delivered`
- 任何情况下都不得把 “没配置 env” 记成 success

### 3.2 Payload shape

W6 不新增新的 cross-repo orchestration API，只发送一个 adapter-feishu-compatible notification payload。

推荐 payload：

```json
{
  "providerKey": "warning-agent",
  "reportId": "rpt_checkout_post_api_pay_20260418t120008z",
  "runId": "ipk_checkout_post_api_pay_20260418t120008z",
  "title": "[P1] checkout POST /api/pay",
  "summary": "checkout POST /api/pay requires page_owner after cloud_fallback investigation",
  "occurredAt": "2026-04-18T12:00:24Z",
  "severity": "critical",
  "bodyMarkdown": "---\nschema_version: alert-report.v1\n...",
  "target": {
    "channel": "feishu",
    "chatId": "oc_xxx"
  },
  "facts": [
    { "label": "service", "value": "checkout" },
    { "label": "operation", "value": "POST /api/pay" },
    { "label": "delivery_class", "value": "page_owner" },
    { "label": "investigation_stage", "value": "cloud_fallback" },
    { "label": "owner", "value": "payments-oncall" }
  ]
}
```

### 3.2.1 Field mapping

| outbound field | source of truth | W6 rule |
|---|---|---|
| `providerKey` | constant | always set to `warning-agent` even if adapter has a default provider |
| `reportId` | `report_record["report_id"]` | required |
| `runId` | `report_record["packet_id"]` | W6 期间把 `packet_id` 作为 stable run anchor；不额外发明新 runtime noun |
| `title` | report frontmatter | format: `[<severity_band>] <service> <operation-or-service>` |
| `summary` | warning-agent delivery payload builder | concise one-line operator summary；不得直接截断整份 Markdown 代替 |
| `occurredAt` | `report_record["generated_at"]` | required on warning-agent side even if adapter marks it optional |
| `severity` | `severity_band` | freeze mapping in W6.S2a；see 3.2.2 |
| `bodyMarkdown` | `report_record["markdown"]` | send full report Markdown |
| `reportUrl` | none yet | omit in W6.S2a/S2b；stable report URL is future work |
| `incidentId` | none yet | omit for now; adapter dedupe falls back to `reportId` |
| `target.channel` | constant | always `feishu` |
| `target.chatId/openId/threadId` | env-gated delivery config | current bridge requires `chatId` or `openId`; `threadId` optional |
| `facts[]` | report/frontmatter | include only short operator-facing facts; do not dump whole packet |
| `actions[]` | none yet | omit in W6.S2a/S2b |

### 3.2.2 Severity mapping

W6 freeze：

- `P1 -> critical`
- `P2 -> warning`
- `P3 -> info`
- `P4 -> info`

不要在 W6.S2a/S2b 内引入更复杂的 multi-channel severity policy。

### 3.3 Delivery config seam

W6 wave-2 首个 live route 只覆盖：`page_owner`。

其它 delivery class 在 W6.S2a/S2b 保持 local durable truth：

- `observe`
- `open_ticket`
- `send_to_human_review`

推荐 config shape（exact field names may still be refined during implementation, but the semantics are frozen here）：

```yaml
routes:
  page_owner:
    adapter: adapter_feishu
    delivery_mode: env_gated_live
    provider_key: warning-agent
    endpoint_env: WARNING_AGENT_ADAPTER_FEISHU_BASE_URL
    timeout_seconds: 5
    target:
      channel: feishu
      chat_id_env: WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID
      open_id_env: WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID
      thread_id_env: WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID
```

Required env rule for W6 first bridge:

- `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL`
- one of:
  - `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID`
  - `WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID`

Optional:

- `WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID`
- `WARNING_AGENT_ADAPTER_FEISHU_TIMEOUT_SECONDS` if implementation prefers env override over yaml literal

### 3.4 Delivery dispatch truth inside warning-agent

W6.S2a/S2b 需要让 warning-agent 的 delivery artifact truth 显式区分：

- `local_durable`
- `env_gated_live`

最小要求：dispatch record 必须能回答以下问题：

- 这次 route 是 `local_durable` 还是 `env_gated_live`
- env gate 是否 ready
- 若 not ready，为什么 deferred/rejected
- 若 request sent，目标 endpoint 是什么
- adapter response 是什么
- 当前最终 status 是 `queued` / `deferred` / `failed` / `delivered`

W6 不强制现在就改名成新的 schema version；只有当现有测试/reader 证明 exact shape 已被依赖时，才需要引入新的 `delivery-dispatch` schema version。

## 4. W6.S2a implementation checklist

S2a 的更细代码级设计、typed route split、env resolver、payload builder 与 test matrix 见：

- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_S2A_FEISHU_CODE_DESIGN.md`


目标：冻结 `adapter_feishu / env_gated_live` seam，但 **不要求** 真实调用 Feishu SaaS。

#### 4.1 Code surfaces

建议触达面：

- `app/delivery/runtime.py`
- 必要时新：
  - `app/delivery/adapter_feishu.py`
  - `app/delivery/payloads.py`
  - `app/delivery/env_gate.py`
- `configs/delivery.yaml`
- `tests/test_delivery.py`
- 新增 targeted tests（例如 `tests/test_delivery_adapter_feishu.py`）

#### 4.2 Concrete tasks

1. 扩展 delivery route model：
   - 让 route 明确携带 `delivery_mode = local_durable | env_gated_live`
   - 让 `page_owner` 能指向 `adapter_feishu`
2. 实现 env gate resolver：
   - resolve base URL
   - resolve Feishu target (`chatId` or `openId`)
   - env missing 时返回 explicit gate result，而不是直接抛出模糊异常
3. 实现 `report_record -> WarningAgentNotificationPayload` builder：
   - freeze `runId = packet_id`
   - freeze severity mapping
   - freeze one-line summary builder
4. 扩展 dispatch record：
   - 至少记下 `delivery_mode`
   - `env_gate_state`
   - `target_channel`
   - `target_ref`
   - `live_endpoint` when configured
5. 保持 stop boundary：
   - 不接真实 Feishu API
   - 不引入 auth / secret manager / callback orchestration
   - 不扩成 multi-provider routing project

#### 4.3 W6.S2a proof set

Targeted tests should prove:

1. config loader 能读出 `adapter_feishu` + `env_gated_live` route
2. env present -> payload builder 产出 adapter-feishu-compatible payload
3. env missing -> dispatch result is explicit `deferred` or `rejected`
4. `page_owner` route 与其余 `local_durable` routes 被显式区分
5. runtime/webhook path 走到 `page_owner` 时不会 silent success

Recommended targeted commands:

- `uv run pytest tests/test_delivery.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py`
- `uv run pytest tests/test_delivery_adapter_feishu.py`

#### 4.4 W6.S2a done-when

只有以下同时成立才算 done：

- `page_owner` 的 live seam 已 frozen to `adapter_feishu`
- delivery config 已显式区分 `local_durable` vs `env_gated_live`
- env missing 时有 explicit deferred/rejected proof
- payload builder contract 已固定且有 tests
- 没有引入 real remote API / auth / callback flow

## 5. W6.S2b implementation checklist

目标：在 warning-agent 内把 `page_owner -> adapter-feishu` 这条最小 live bridge 跑通，并给出 honest smoke proof。

#### 5.1 Code surfaces

建议触达面：

- `app/delivery/runtime.py`
- `app/runtime_entry.py`
- 必要时新：
  - `app/delivery/http_client.py`
  - `app/delivery/bridge_result.py`
- `tests/test_runtime_entry.py`
- `tests/test_alertmanager_webhook.py`
- `tests/test_delivery_adapter_feishu.py`

#### 5.2 Concrete tasks

1. 实现 bounded HTTP bridge client：
   - `POST /providers/webhook`
   - parse adapter JSON response
   - strict success criteria = `202 + code=0 + status in {delivered, duplicate_ignored}`
2. 把 `env_gated_live` route 接入 runtime/webhook delivery path：
   - env ready -> fire request
   - env missing -> do not fire request
3. 把 adapter response 写回 delivery dispatch truth：
   - `status`
   - `response_code`
   - `provider_key`
   - `external_ref` if returned later
   - error message on failure/deferred
4. 保持 fail-closed：
   - non-202 / invalid JSON / timeout -> `failed`
   - missing env -> `deferred` / `rejected`
   - do not backfill local success state after live failure unless a later pack explicitly designs dual-write policy
5. direct smoke should prefer real adapter-feishu runtime over a fake arbitrary webhook stub：
   - use local `adapter-feishu` repo
   - boot its provider-webhook path with fake Feishu client / reply sink so no real Feishu SaaS credential is needed for smoke
   - then run warning-agent replay/webhook path against that local adapter host

#### 5.3 W6.S2b proof set

Targeted tests should prove:

1. env missing -> no outbound HTTP request; dispatch status is `deferred`/`rejected`
2. env ready + adapter returns `202/code=0/delivered` -> warning-agent marks live dispatch delivered
3. adapter returns `duplicate_ignored` -> warning-agent treats bridge as accepted non-error
4. adapter returns non-202 or malformed response -> warning-agent marks failed
5. webhook path and replay/runtime path both hit the same live bridge logic

Recommended targeted commands:

- `uv run pytest tests/test_delivery_adapter_feishu.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py`

Recommended direct smoke shape:

1. in sibling repo `adapter-feishu`, start a local runtime or harness that exposes `/providers/webhook` and uses fake Feishu send deps
2. in `warning-agent`, run a bounded replay or TestClient-triggered webhook execution with:
   - `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL=http://127.0.0.1:<port>`
   - `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID=<local-test-chat>`
3. assert direct proof:
   - warning-agent dispatch record status = `delivered`
   - adapter returned provider status = `delivered` or `duplicate_ignored`
   - no silent fallback occurred

#### 5.4 W6.S2b done-when

只有以下同时成立才算 done：

- warning-agent 能把一个真实 report notification POST 到 `adapter-feishu /providers/webhook`
- env missing 时显式 deferred/rejected
- env present 时最小 bridge proof 成立
- runtime/webhook 两条 delivery path 均经过同一 live bridge logic
- 未扩张到 callback orchestration、report polling、alert-forward API、multi-env auth/secrets

## 6. Non-goals inside W6.S2a/S2b

以下工作不在当前 slice 内：

- `warning-agent` 对外暴露 `GET /reports/:id` 或 submit/report orchestration API
- `adapter-feishu` 从 warning-agent 拉取 report 而不是接收 push
- Feishu card action callback workflow
- multi-chat / multi-tenant routing
- PagerDuty/Jira/Slack multi-vendor matrix
- real Feishu SaaS rollout hardening / credential governance / secret manager

## 7. Replan triggers

命中任一项必须停下并回到 replan，而不是把 W6.S2* 扩成集成大包：

1. 证明最小 bridge correctness 必须先实现稳定 `warning-agent` report API。
2. 证明最小 smoke 必须依赖真实 Feishu remote API，而无法通过 local fake client/reply sink 完成。
3. live bridge 需要 multi-env auth / secret manager / deployment platform 才能继续。
4. `page_owner` route 被证明不足以承载 first vendor bridge，导致必须同时重做多条 delivery class。
5. 为完成 Feishu bridge，必须跨入 callback orchestration 或 adapter-side long-term state redesign。
