# warning-agent signoz warning production plan

- plan_id: `warning-agent-signoz-warning-production-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / W7 complete`
- predecessor_plan: `warning-agent-production-integration-bridge-2026-04-20`
- draft_input: `docs/debt/warning-agent-w7-signoz-warning-production-plan-draft.md`
- last_updated: `2026-04-20`

## 1. Goal

在 `W6 production integration bridge` honest closeout 之后，启动第一个真正面向 **production Signoz warning ingress + governed processing** 的 successor pack：

> 把当前已经落地的 `Signoz-first` runtime，
> 从“CLI / smoke / local proof 可跑通”的状态，
> 推进到“真实 Signoz warning 能通过受治理入口进入系统、留下 durable truth、经过 bounded queue/worker 边界、再稳定进入 packet -> analyzer -> investigation -> report 主链路”的状态，
> 但**不提前宣称 production rollout completed**。

本 pack 的主目标不是重写 analyzer / investigator 哲学，而是把已经存在的 Signoz-first runtime 收敛成生产可治理的 warning plane：

```text
Signoz warning
  -> governed ingress
  -> durable admission truth
  -> dedupe + queue ledger
  -> worker boundary
  -> packet / analyzer / investigation / report
  -> delivery / feedback / audit evidence
```

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/warning-agent-architecture.md`
- `docs/warning-agent-signoz-first-runbook.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-integration-rollout-evidence.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_CLOSEOUT.md`
- `docs/plan/warning-agent-w7-successor-replan-input-2026-04-20.md`
- `docs/debt/warning-agent-w7-signoz-warning-production-plan-draft.md`
- 当前 repo reality：
  - `app/receiver/signoz_alert.py`
  - `app/receiver/alertmanager_webhook.py`
  - `app/runtime_entry.py`
  - `app/live_signoz_smoke.py`
  - `app/collectors/*`
  - `app/packet/*`
  - `app/reports/*`
  - `app/investigator/*`
  - `app/storage/*`
  - `tests/*`

## 3. Scope

### In scope

- dedicated Signoz warning ingress route and caller contract freeze
- durable raw / normalized / receipt / provenance admission truth
- dedupe key and queue / ledger baseline for accepted warnings
- worker lease / retry / dead-letter boundary that decouples ingress from analysis execution
- admitted warning -> current `packet -> analyzer -> optional investigation -> report` chain wiring
- explicit failure visibility for evidence-partial / investigation-fail-closed / delivery-deferred paths
- operator-visible readiness / backlog / rollout checklist truth for the new warning plane
- W7 reality audit and successor residual freeze

### Out of scope

- building a new observability platform or continuous SigNoz polling data plane
- rewriting local analyzer / investigator product philosophy
- collapsing auth / queue / deployment / secret / provider governance into one oversized slice
- multi-environment secret-manager or deployment-platform build-out
- unlimited logs / traces scanning in worker hot path
- claiming `production-ready rollout completed` before W7 audit evidence exists

## 4. Why this plan exists

当前 repo 已经证明：

1. `signoz_alert` 已是 current primary warning input contract。
2. Signoz-first packet / decision / investigation / report 主链可以在 CLI / smoke path 上跑通。
3. delivery seam、provider runtime gate、operator-visible rollout evidence baseline 已在 W6 落地。

但当前 repo **仍然没有**证明：

1. 真实 Signoz warning 可以通过受治理的 external ingress surface 长期进入系统。
2. ingress 不依赖同步完整 runtime 执行，也不会把 HTTP 生命周期直接绑死到整条分析链路。
3. accepted warning 拥有 raw payload、normalized warning、receipt、provenance、queue status 的 durable truth。
4. duplicate firing、retry、worker crash、dead-letter 这些生产边界有明确 contract。
5. `/readyz` 能诚实报告 warning ingress / queue / backlog / failure / deferred state，而不只是服务在线。

W7 的目标就是把这些 production claim blocker 收敛成 serial、可验证、可 honest handoff 的 warning plane，而不是继续停留在本地 smoke 成功的叙事里。

## 5. Execution principles

1. **ingress before worker**：先定义什么叫“合法进入系统的 Signoz warning”，再做 queue / worker。
2. **durable truth before automation**：先留下 raw / normalized / receipt / provenance / queue truth，再谈更自动的处理链。
3. **strict serial**：一次只允许一个 `active_slice`，禁止 ingress / queue / worker / runtime 并行膨胀。
4. **fail closed over silent best-effort**：caller/auth 不满足、payload malformed、worker unavailable、investigation budget hit 时，优先显式 rejected / deferred / human-review handoff。
5. **reuse the current runtime spine**：W7 只能把 admitted warning 接到现有 `packet -> analyzer -> investigation -> report` spine；不得长出第二套 analyzer / investigator。
6. **review-gated closeout**：W7 结束前必须做 reality audit；不得把 W7 直接宣称为 production rollout completed。

## 6. Wave decomposition

### wave-1 / W7 governed Signoz ingress baseline

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W7.S1a` governed Signoz ingress route + caller contract freeze | `app/receiver/signoz_alert.py`、必要时新 `app/receiver/signoz_ingress.py` / app factory glue、`tests/test_signoz_ingress_api.py`、相关 API tests | TestClient proof：dedicated Signoz route 对 live-like payload 返回 explicit `accepted / rejected / deferred` receipt；caller/auth / malformed payload / unsupported state 都有显式 contract；不依赖同步完整 runtime 执行 | 不做 durable queue / worker；不在 ingress handler 里同步跑完整 analyzer / investigation |
| `W7.S1b` durable warning admission ledger + provenance truth | ingress receipt persistence、`app/storage/*`、必要时新 admission helper module、`tests/test_signoz_admission_storage.py` | accepted warning 会留下 raw payload、normalized warning、admission receipt、caller/provenance truth；metadata / artifact paths 可直接证明 durable admission landed | 不做 dedupe / retry / worker lease；不改 analyzer 路由 |

### wave-2 / W7 warning processing boundary

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W7.S2a` dedupe key + queue ledger contract | 必要时新 queue / ledger module、`app/storage/*`、`tests/test_signoz_queue_contract.py` | repeated firing 在固定 eval window 内拥有 deterministic dedupe key；queue / ledger 至少显式区分 `pending / processing / completed / failed / dead_letter / deduped`；direct record proof 可见 | 不做 worker runtime；不接外部分布式 message bus |
| `W7.S2b` worker lease / retry / dead-letter boundary | 必要时新 worker module、queue runtime glue、`tests/test_signoz_worker_runtime.py` | worker 只消费 durable accepted warnings；transient failure 有 retry/backoff proof；poison message 进入 dead-letter；worker crash 后可恢复继续消费 | 不重写 analyzer / investigation body；不做 broad rollout orchestration |

### wave-3 / W7 production analysis bridge

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W7.S3a` admitted warning -> packet / analyzer / report handoff | `app/runtime_entry.py`、`app/collectors/evidence_bundle.py`、`app/packet/*`、`app/reports/*`、worker glue、runtime tests | worker 消费 admitted warning 后，可稳定 materialize packet / decision / optional investigation / report；每阶段 artifact 可直接证明 | 不允许长出第二套 analyzer / investigator；不在 worker 中做无边界 observability 扫描 |
| `W7.S3b` partial-evidence / delivery-deferred failure contract | `app/runtime_entry.py`、`app/investigator/*`、`app/delivery/*`、artifact / metadata writeback、相关 tests | evidence partial、investigation fail-closed、delivery deferred、human-review handoff 都有显式 machine-readable state；不会 silent success | 不改产品边界；不把 cloud fallback 重新长成默认推理平面 |

### wave-4 / W7 operator governance + closeout

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W7.S4a` operator readiness + rollout checklist truth | `app/integration_evidence.py`、shared readiness surface、必要时 docs/runbook/tests 更新 | `/readyz` 或等价 operator surface 现在能直接报告 ingress auth state、queue health、backlog size、oldest pending age、deduped count、processing failure count、delivery deferred count、fallback ratio；环境 checklist 可读 | 不宣称 production-ready；不做多环境 secret / deployment platform |
| `W7.RV1` execution reality audit + successor replan input | evidence-driven audit、closeout doc、successor replan input | reality audit verdict=`accept` or `accept_with_residuals`；remaining residuals honest frozen；next pack input written | 不 claim production-ready unless evidence truly supports it |

## 7. Validation ladder

W7 默认验证顺序固定为：

1. targeted unit / contract / API tests
2. targeted ingress / queue / worker / runtime smoke
3. direct proof for the affected durable surface
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

slice-specific notes：

- `W7.S1a` 必须证明 dedicated Signoz route 的 receipt contract 明确区分 `accepted / rejected / deferred`。
- `W7.S1b` 必须证明 accepted warning 留下 raw / normalized / receipt / provenance durable truth，而不是只有 HTTP 200。
- `W7.S2a` 必须证明 dedupe key 与 queue state 是 deterministic 且可回读的。
- `W7.S2b` 必须证明 worker crash / retry / dead-letter 行为可直接证明，不依赖口头叙述。
- `W7.S3a` 必须证明 admitted warning 进入的是当前 canonical runtime spine，而不是第二套分析路径。
- `W7.S3b` 必须证明 failure / deferred / human-review 是显式 machine truth，而不是 silent drop。
- `W7.S4a` 必须证明 operator 能看见 ingress / queue / fallback / delivery gate truth，而不是只看 healthz。

没有对应 evidence，不得 claim slice done。

## 8. W7 closeout rule

W7 只能在以下同时成立时 closeout：

- 真实 Signoz warning 已拥有 dedicated governed ingress surface
- accepted warning 已拥有 durable raw / normalized / receipt / provenance truth
- queue / ledger / worker boundary 已显式 landed，warning 不再绑死在 HTTP 生命周期内
- admitted warning 已能稳定进入当前 canonical runtime spine，并产出 packet / decision / optional investigation / report
- operator surface 已能直接判断 ingress / queue / backlog / deferred / fallback state
- `W7.RV1` reality audit 通过
- remaining residuals 已明确路由到 successor pack，而不是继续混在 W7 中

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. Signoz ingress correctness 被证明离不开完整 multi-env auth / secret platform 才能做最小验证。
2. queue / worker baseline 被证明离不开外部分布式 message bus，导致 repo-local minimal proof 失效。
3. admitted-warning runtime wiring 被证明需要重写 analyzer / investigator canonical contract，而不只是 glue。
4. operator readiness truth 被证明需要 deployment platform 或跨环境 orchestration 才能最小成立。
5. W7 执行中再次混入“production rollout completed” narrative，但 evidence 不足。

## 10. Exit / successor rule

- 本 pack 是 `W6 production integration bridge` closeout 之后的 warning-plane successor control plane。
- W7 完成后，若继续推进，下一 pack 应聚焦：
  - env-specific auth / secret / rollout hardening
  - queue scaling / retention / replay governance
  - delivery policy hardening on real admitted warnings
  - post-incident feedback compounding on durable production warning truth
- 在这些 successor work 完成前，repo 不得诚实声称 `production-ready rollout completed`。
