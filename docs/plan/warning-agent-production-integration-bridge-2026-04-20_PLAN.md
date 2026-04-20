# warning-agent production integration bridge plan

- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- plan_class: `execution-plan`
- status: `in_progress`
- mode: `autopilot-control-plane`
- current_wave: `wave-4 / W6 rollout evidence hardening`
- last_updated: `2026-04-20`

## 1. Goal

在 `W5 production readiness foundation` honest closeout 之后，启动第一个真正面向 external integration 的 successor pack：

> 把当前 `warning-agent` 从“foundation layer 已收口、但 external surfaces 仍 mostly local/deterministic”
> 推进到“更接近真实 operator / vendor / provider integration bridge”的状态，
> 但**不提前宣称 production rollout completed**。

本 pack 的主目标不是继续补本地 demo 能力，而是把 W5 留下的几个真实 production bridge 缺口收敛成可验证、可续做、可 honest handoff 的 integration layer：

```text
external landed outcome admission
  -> durable feedback refresh
  -> vendor-facing delivery seam
  -> real provider adapter seam
  -> rollout / observability evidence bridge
```

当前 successor pack 重点收敛的是：

- external outcome admission baseline
- durable outcome receipt / retrieval refresh glue
- live vendor delivery adapter contract
- real provider adapter contract + runtime gating
- rollout / observability hardening for the new external surfaces

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/warning-agent-architecture.md`
- `docs/warning-agent-provider-boundary.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-feedback-governance.md`
- `docs/plan/warning-agent-production-readiness-foundation-2026-04-20_CLOSEOUT.md`
- `docs/plan/warning-agent-production-readiness-foundation-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_FEISHU_DELIVERY_BRIDGE.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_S2A_FEISHU_CODE_DESIGN.md`
- 当前 repo reality：
  - `app/feedback/outcome_ingest.py`
  - `app/feedback/persistence.py`
  - `app/feedback/retrieval_refresh.py`
  - `app/receiver/alertmanager_webhook.py`
  - `app/delivery/*`
  - `app/investigator/*`
  - `app/runtime_entry.py`
  - `configs/delivery.yaml`
  - `configs/collectors.yaml`
  - `configs/provider-boundary.yaml`
  - `tests/*`

## 3. Scope

### In scope

- external operator-facing outcome admission API baseline
- durable outcome admission receipt + retrieval refresh/runtime glue
- live vendor delivery adapter contract and env-gated local proof
- real provider adapter contract + runtime glue before full rollout
- rollout / observability evidence hardening for the new integration surfaces
- W6 closeout review and W7 replan input

### Out of scope

- full multi-environment secret manager / auth rollout
- distributed queue / message bus platform build-out
- production-wide deployment orchestration
- autonomous remediation / workflow engine
- unbounded vendor exploration or broad infra migration
- claiming production-ready rollout before W6 reality audit and successor residual freeze

## 4. Why this plan exists

W5 已把 foundation layer honest 收口，但 closeout 同时冻结了几类仍阻断真实 production claim 的 successor residuals：

1. landed outcome ingest 目前仍是 repo-local function path，不是 operator-facing external admission surface。
2. delivery plane 目前只有 durable local queue artifact；还没有 live vendor adapter seam。
3. provider boundary 虽然已 fail closed，但 provider 本体仍是 deterministic smoke，不是 real adapter/runtime bridge。
4. rollout / observability hardening 目前只覆盖 foundation truth，不覆盖新的 external integration surfaces。

W6 的目标不是一次性把所有 external integration 直接做成真实线上系统，而是先把这些缺口收敛成：

- 明确 contract
- 显式 gate
- env-gated integration seam
- honest failure / fallback rule

这样后续真正进入 vendor credential、deployment、multi-env rollout 时，不会再建立在 repo-local stub 或 silent drift 上。

## 5. Execution principles

1. **contract before credential**：先冻结 API / adapter / receipt / gating contract，再碰 live credential 或 rollout。
2. **strict serial**：一次只允许一个 `active_slice`，不让 outcome admission、delivery、provider、rollout 同时膨胀。
3. **TDD-first**：每个 slice 先补 proof-carrying test，再落实现。
4. **fail closed over silent best-effort**：external surface 若缺依赖、缺 config、缺 credential，优先显式 handoff / rejected / review queue，不做 silent pretend success。
5. **env-gated integration**：W6 可引入 live seam，但不能把“未配置环境”误说成“已完成 vendor rollout”。
6. **review-gated closeout**：W6 结束前必须做 reality audit；不得把 W6 直接宣称为 production rollout completed。

## 6. Wave decomposition

### wave-1 / W6 external outcome admission bridge

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W6.S1a` external outcome admission API baseline | `app/feedback/outcome_ingest.py`、必要时新 `app/feedback/outcome_api.py` / app factory glue、API tests | TestClient proof：explicit success/error receipt；outcome / metadata / retrieval refresh all landed | 不引入 auth / queue / deployment infra |
| `W6.S1b` durable outcome receipt + feedback refresh glue | outcome admission receipt/runtime glue、feedback docs/tests | accepted outcome 会触发 durable receipt + retrieval refresh + evidence trail | 不改 promotion policy；不做 multi-env auth |

### wave-2 / W6 vendor delivery bridge

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W6.S2a` live delivery adapter contract + env config seam | `app/delivery/*`、`configs/delivery.yaml`、tests；first vendor frozen to `adapter-feishu` on `page_owner` route | route contract 显式区分 `local_durable` vs `env_gated_live`；`report -> adapter-feishu WarningAgentNotificationPayload` mapping frozen；targeted delivery tests pass | 不接真实 SaaS API |
| `W6.S2b` first vendor delivery smoke bridge | first vendor frozen to `warning-agent -> adapter-feishu -> Feishu/Lark`；runtime/webhook glue + tests + local adapter smoke | env missing 时显式 rejected/deferred；env present 时最小 smoke path 有 direct proof；不得偷渡成 alert-forward orchestration | 不扩成 full rollout orchestration |

### wave-3 / W6 real provider bridge

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W6.S3a` real provider adapter contract freeze | `app/investigator/*`、`configs/*`、tests | deterministic smoke 与 future real adapter contract 被显式区分；adapter config surface frozen | 不接 serving deployment |
| `W6.S3b` provider runtime glue + fail-closed rollout gate | runtime/provider invocation glue、tests、docs | env missing / provider unavailable 时显式 fail closed；env present 时最小 provider bridge proof pass | 不做 broad vendor optimization |

### wave-4 / W6 rollout evidence hardening

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W6.S4a` integration observability + rollout evidence baseline | rollout docs/scripts/tests、必要时 metrics/logging truth | new external surfaces 有 health / readiness / operator evidence；targeted smoke + docs proof | 不做 multi-env deployment platform |
| `W6.RV1` execution reality audit + W7 replan input | evidence-driven audit + residual freeze | reality audit verdict=`accept` or `accept_with_residuals`；W7 replan input written | 不 claim production-ready unless evidence truly supports it |

## 7. Validation ladder

W6 默认验证顺序固定为：

1. targeted unit / contract / API tests
2. targeted smoke / env-gated probe
3. direct proof for the affected surface
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

slice-specific notes：

- `W6.S1a` 必须证明 external outcome admission 不再只是 repo-local function path
- `W6.S1b` 必须证明 admitted outcome 会留下 durable receipt / retrieval refresh evidence
- `W6.S2a` 必须证明 delivery contract 显式区分 local durable route 与 live vendor seam，并冻结首个 `adapter-feishu` payload/env contract
- `W6.S2b` 必须证明 env missing 时不会 silent success，并给出 `warning-agent -> adapter-feishu -> Feishu/Lark` 的最小 direct proof
- `W6.S3a` 必须证明 deterministic smoke 与 future real provider contract 被显式切开
- `W6.S3b` 必须证明 provider unavailable 时显式 fail closed 到 review / handoff
- `W6.S4a` 必须证明 external integration surfaces 具有 operator-visible health/readiness/evidence

没有对应 evidence，不得 claim slice done。

## 8. W6 closeout rule

W6 只能在以下同时成立时 closeout：

- external landed outcome admission 不再只是 repo-local function path
- delivery plane 至少存在一个 env-gated live vendor adapter seam
- provider plane 不再只剩 deterministic smoke truth，而有 real adapter contract + runtime gate
- rollout / observability evidence 至少覆盖新的 external surfaces
- `W6.RV1` reality audit 通过
- remaining residuals 已明确路由到 W7，而不是继续混在 W6 中

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. outcome admission baseline 需要外部 auth / queue / deployment infra 才能验证最小正确性。
2. live vendor delivery smoke 被证明离不开真实 credential / remote API 才能做最小 proof。
3. provider bridge 被证明离不开 serving deployment / vendor SDK migration 项目。
4. rollout evidence hardening 需要 multi-env secret manager 或大规模 deployment orchestration。
5. W6 reality audit 发现当前 workstream 已混入“production rollout complete” narrative，但 evidence 不足。

## 10. Exit / successor rule

- 本 pack 是 `W5 production readiness foundation` closeout 之后的第一个 integration-bridge successor control plane。
- W6 完成后，若继续推进，下一 pack 应聚焦：
  - environment-specific rollout
  - live vendor scaling / tuning
  - multi-env auth / secret / deployment governance
  - post-rollout feedback compounding on real admitted outcomes
- 在这些 successor work 完成前，repo 不得诚实声称 `production-ready rollout completed`。
