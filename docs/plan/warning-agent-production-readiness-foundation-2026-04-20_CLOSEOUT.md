# warning-agent production readiness foundation closeout

- plan_id: `warning-agent-production-readiness-foundation-2026-04-20`
- closeout_date: `2026-04-20`
- verdict: `accept_with_residuals`
- next_handoff: `replan-required`

## 1. Scope audited

审计对象：`W5 production readiness foundation`

claimed outcomes：

- packaged console-script / module mode parity 已 landed
- runtime metadata truth 已跟随 active control-plane pack 同步
- runtime scoring path 已真实消费 retrieval hits
- webhook/operator plane baseline 已具备 explicit health/readiness/error receipt contract
- delivery class 已进入 durable local adapter outputs
- collector endpoints / SigNoz settings 已外置到 config，不再依赖 collector code 内藏地址常量
- provider boundary 与 fail-closed human-review rule 已显式冻结

## 2. Findings

### confirmed

1. packaged entrypoint truth 已真实落地：
   - `uv run warning-agent ...` 与 `python -m app.main ...` 共用同一 argv resolution path
2. runtime metadata truth 已真实落地：
   - `app.main.get_app_metadata()` 现在优先读取 active plan pack；若无 active pack，则回退到最新 completed pack terminal truth
3. retrieval-informed runtime scoring 已真实落地：
   - `app/runtime_entry.py` 已不再固定传 `retrieval_hits=[]`
   - seeded outcome retrieval proof 已证明 replay / live runtime path 能把 non-empty retrieval hits 传给 scorer
4. operator plane baseline 已真实落地：
   - `app/receiver/alertmanager_webhook.py` 现在提供 `/healthz` / `/readyz`
   - success / error receipt contract 已冻结为 `alertmanager-webhook-receipt.v1`
   - invalid runtime input 现在返回 explicit `422 runtime_validation_error`
5. delivery plane baseline 已真实落地：
   - 新增 `app/delivery/runtime.py`
   - 新增 `configs/delivery.yaml`
   - runtime / webhook path 现在都会持久化 `deliveries/deliveries.jsonl` 与 queue-specific Markdown payload
6. collector config externalization 已真实落地：
   - 新增 `configs/collectors.yaml`
   - `PrometheusCollector` / `SignozCollector` 默认值现在从 config 读取
   - grep proof 已确认 collector code 中不再保留 active endpoint/base_url 字面量
7. provider boundary 已真实落地：
   - 新增 `configs/provider-boundary.yaml`
   - 新增 `app/investigator/provider_boundary.py`
   - degraded local fallback 与 cloud-fallback unavailable path 现在都会 fail closed 到 `send_to_human_review`
   - 新增 `docs/warning-agent-provider-boundary.md`
8. full regression / hygiene 通过：
   - `uv run pytest` → `128 passed`
   - `uv run ruff check app tests scripts` → pass

### drift fixed

1. predecessor drift：console-script path 失效，而 module mode 正常。
2. predecessor drift：runtime metadata 会静默停留在历史 predecessor phase。
3. predecessor drift：runtime / webhook scoring path 对 retrieval hits 存在 duplicated `[]` hard-code。
4. predecessor drift：operator plane 只有 webhook stub，没有 explicit receipt / health / readiness / error contract。
5. predecessor drift：delivery class 只存在于 Markdown frontmatter，没有 durable adapter output。
6. predecessor drift：Prometheus / SigNoz collector settings 藏在 code 常量里。
7. predecessor drift：provider unavailable 时不会 fail closed 到 human review。

### uncertain

none remaining inside current W5 foundation scope.

## 3. Evidence added / reused

### targeted tests

- `uv run pytest tests/test_bootstrap.py tests/test_live_runtime_entry.py`
- `uv run pytest tests/test_runtime_entry.py tests/test_live_runtime_entry.py tests/test_retrieval.py`
- `uv run pytest tests/test_alertmanager_webhook.py tests/test_live_runtime_entry.py`
- `uv run pytest tests/test_delivery.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py`
- `uv run pytest tests/test_prometheus_collector.py tests/test_signoz_collector.py tests/test_live_evidence_bundle.py tests/test_live_runtime_entry.py`
- `uv run pytest tests/test_provider_boundary.py tests/test_fallback.py tests/test_cloud_fallback.py`

### direct proof

- `uv run warning-agent replay fixtures/replay/manual-replay.checkout.high-error-rate.json`
- seeded runtime retrieval probe → scorer input contained non-empty retrieval hits
- operator probe → `/healthz`, `/readyz`, explicit `422 runtime_validation_error`, webhook retrieval hits persisted
- runtime / webhook delivery probe → durable `deliveries` records and queue payload Markdown landed
- grep proof → collector code no longer contains live endpoint/base_url literals
- provider failure probe → local/cloud unavailable path both fail closed to `send_to_human_review`

### full gates

- `uv run pytest` → `128 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during W5

- packaged CLI / metadata truth sync
- retrieval-informed runtime scoring wiring
- operator-facing admission API baseline
- durable local delivery adapter contract
- collector config externalization
- explicit deterministic-smoke provider boundary + human-review fail-closed rule
- terminal metadata truth fallback to latest completed pack

## 5. Successor residuals / W6 replan input

1. current delivery adapters are **local durable queues only**；仍未接 PagerDuty/Jira/Slack live vendor integration。
2. current provider boundary 仍是 **deterministic smoke**；仍未进入 real provider / model / serving integration。
3. current webhook/operator plane 是 local baseline；external auth、queue infra、多环境 admission 仍未 materialize。
4. collector config 已 externalized，但 multi-env secret management / rollout governance 仍未进入当前 pack。
5. 因以上 residuals 仍存在，repo 现在只能诚实声称：
   - `production-readiness foundation landed`
   - **not** `production-ready rollout completed`

推荐 W6 successor theme：

- real provider integration
- external outcome admission
- live vendor delivery integration
- rollout / observability hardening

## 6. Closeout verdict

`W5` 可以 honest closeout 为 `completed`，并带 successor residuals。

理由：

- plan 中定义的 foundation layer 六类缺口都已被代码、tests、config、probe、control-plane 共同支撑。
- 当前 scope 内已无未证实 claim。
- remaining residuals 都属于 successor rollout / vendorization / externalization work，而不是 W5 foundation 未闭合 implementation。

## 7. Successor handoff

- 当前停止在 `review / replan` boundary。
- 若继续推进，必须新开 successor `PLAN / STATUS / WORKSET`，而不是回滚重开 W5 slice。
