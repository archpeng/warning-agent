# warning-agent minimax local-primary real adapter plan

- plan_id: `warning-agent-minimax-local-primary-real-adapter-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- predecessor_plan: `warning-agent-signoz-warning-production-2026-04-20`
- priority_input: `docs/debt/warning-agent-minimax-m2.7-highspeed-3.6-integration-path.md`
- last_updated: `2026-04-20`
- closeout_artifact: `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_CLOSEOUT.md`

## 1. Goal

在 `W7 signoz warning production` honest closeout 之后，围绕用户点名的 bounded debt doc，启动一个新的 successor pack：

> 保持当前 `warning-agent` 的 `local-first investigator` 架构与 `InvestigationRequest -> InvestigationResult` 契约不变，
> 只把 `local_primary.real_adapter` 这条 seam 真正接通，
> 让 `neko api:minimax-m2.7-highspeed` 可以作为 `3.6 Investigation` 的真实本地调查模型，
> 但**不顺手扩 scope 到 ingress / queue / delivery / cloud fallback rollout**。

本 pack 的主目标不是重做 analyzer / investigator 产品逻辑，而是把当前已经存在的 `real_adapter gate` 从“可注入 fake provider 的 contract seam”推进到“runtime 可自动装配的 real local-primary provider”状态：

```text
provider-boundary contract
  -> local_primary real adapter client
  -> runtime auto-wiring
  -> schema-valid InvestigationResult
  -> targeted runtime proof
```

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/debt/warning-agent-minimax-m2.7-highspeed-3.6-integration-path.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_CLOSEOUT.md`
- 当前 repo reality：
  - `app/investigator/local_primary.py`
  - `app/investigator/provider_boundary.py`
  - `app/investigator/runtime.py`
  - `tests/test_local_primary.py`
  - `tests/test_provider_boundary.py`
  - `tests/test_investigation_runtime.py`
  - `configs/provider-boundary.yaml`

## 3. Scope

### In scope

- local_primary real-adapter env contract freeze for the Minimax/Neko path
- optional API-key semantics in `provider-boundary` when the local provider requires auth
- bounded OpenAI-compatible local-primary provider implementation
- automatic runtime wiring when `local_primary.real_adapter` gate becomes `ready`
- schema-valid `InvestigationResult` mapping from the real adapter path
- targeted unit / runtime tests and optional env-opt smoke proof surface
- honest closeout / residual freeze for this bounded adapter integration

### Out of scope

- changing `InvestigationRequest -> InvestigationResult` canonical contract
- changing analyzer / router / packet / report product philosophy
- ingress / queue / worker / delivery work from W7
- cloud-fallback live rollout
- multi-model orchestration or generic SDK platformization
- claiming full production-ready model rollout before audit evidence exists

## 4. Why this plan exists

当前 repo 已经证明：

1. `local_primary.real_adapter` 的 boundary contract 已存在。
2. `openai_compatible_http` transport 已是允许的 local-primary boundary transport。
3. gate 语义 `smoke_default / missing_env / ready` 已 landed。
4. tests 已证明 gate ready 时可以消费 injected fake provider。

但当前 repo **仍然没有**证明：

1. runtime 会自动构造一个真实的 `local_primary real_adapter_provider`。
2. `WARNING_AGENT_LOCAL_PRIMARY_*` env 设置本身足以让 runtime 使用真实 provider。
3. real adapter response 可以被稳定映射成 schema-valid `InvestigationResult`。
4. local-primary API key contract 在需要鉴权时被明确表达与验证。

因此，这不是“只配 env 就行”的任务；但也不是需要重做架构的大改。它是一个 **bounded adapter integration**，应被压成严格串行、可验证、可 honest handoff 的小型 successor pack。

## 5. Execution principles

1. **contract before client**：先冻结 `provider-boundary` 与 env 语义，再写 adapter client。
2. **single seam only**：只接通 `local_primary.real_adapter`，不扩到 cloud fallback 或别的 provider family。
3. **test-first**：先补 proof-carrying test，再落实现。
4. **fail closed over silent fallback**：env 缺失、client 缺失、response 不合法时，必须显式 fail closed。
5. **bounded prompt / bounded transport**：adapter 只消费当前 investigation contract 允许的压缩输入，不拼接无边界 observability flood。
6. **review-gated closeout**：结束前必须做 reality audit；不得把 bounded adapter integration 误写成 broader production rollout claim。

## 6. Wave decomposition

### wave-1 / MM local-primary contract and client baseline

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `MM.S1a` boundary contract freeze + API-key semantics | `app/investigator/provider_boundary.py`、`configs/provider-boundary.yaml`、`tests/test_provider_boundary.py` | local-primary real-adapter contract 能诚实表达 Minimax/Neko path 的 endpoint/model/(optional)api-key 语义；targeted boundary tests pass | 不写 runtime client；不改 analyzer/router |
| `MM.S1b` OpenAI-compatible local-primary adapter client baseline | 新 `app/investigator/local_primary_openai_compat.py`、`tests/test_local_primary_openai_compat.py` | fake OpenAI-compatible response 可被映射成 schema-valid `InvestigationResult`；adapter unit tests pass | 不接 runtime auto-wiring；不扩到 generic SDK layer |

### wave-2 / MM runtime seam materialization

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `MM.S2a` local_primary auto-wiring + runtime seam | `app/investigator/local_primary.py`、`app/investigator/runtime.py`、`tests/test_local_primary.py`、`tests/test_investigation_runtime.py` | gate=`ready` 且未显式注入 fake provider 时，runtime 会自动装配 real local-primary provider；targeted runtime tests pass | 不改 packet/analyzer/report contracts；不碰 cloud fallback rollout |
| `MM.S2b` runtime verification + env-opt smoke surface | targeted tests、必要时小型 smoke harness / runbook note | missing API key / missing client / runtime path / optional env-opt smoke 都有 direct proof；`uv run pytest` + `uv run ruff check app tests scripts` through | 默认验证不依赖 live endpoint；不把 smoke 变成 mandatory CI gate |

### wave-3 / MM audit and residual freeze

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `MM.RV1` execution reality audit + successor residual freeze | evidence-driven audit、closeout doc、successor residual note | reality audit verdict=`accept` or `accept_with_residuals`；remaining residuals honest frozen | 不 claim broader production rollout unless evidence truly supports it |

## 7. Validation ladder

本 pack 默认验证顺序固定为：

1. `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py`
2. adapter-specific unit tests（新增 `tests/test_local_primary_openai_compat.py`）
3. `uv run pytest tests/test_investigation_runtime.py`
4. optional env-opt smoke proof if a local Neko endpoint is available
5. `uv run pytest`
6. `uv run ruff check app tests scripts`

slice-specific notes：

- `MM.S1a` 必须先证明 boundary/env contract 已冻结，再进入 client implementation。
- `MM.S1b` 必须证明 adapter 直接输出 schema-valid `InvestigationResult`，而不是半成品 SDK response。
- `MM.S2a` 必须证明 runtime auto-wiring 成立，不再只依赖外部注入 fake provider。
- `MM.S2b` 必须证明 missing API key / missing client / ready gate / runtime path 都有明确 evidence。

没有对应 evidence，不得 claim slice done。

## 8. Closeout rule

本 pack 只能在以下同时成立时 closeout：

- local-primary real-adapter env contract 已显式冻结
- bounded OpenAI-compatible provider 已 landed
- runtime 在 gate=`ready` 时可自动装配 real provider
- real-adapter path 可生成 schema-valid `InvestigationResult`
- missing setup / missing env / unavailable client 仍会显式 fail closed
- `MM.RV1` reality audit 通过
- remaining residuals 已明确路由，而不是继续混在当前 pack 中

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. `neko api` 并非 OpenAI-compatible HTTP，导致需要新增 transport family。
2. real-adapter path 被证明需要修改 canonical `InvestigationRequest` / `InvestigationResult` contract。
3. local-primary integration 被证明会强迫 cloud fallback / analyzer / report 同步重构。
4. bounded adapter integration 被 scope creep 成 generic multi-provider SDK platform。
5. execution 中再次混入 broader production rollout claim，但 evidence 不足。

## 10. Exit / successor rule

- 本 pack 是一个用户点名的 bounded successor pack，优先级来自 `docs/debt/warning-agent-minimax-m2.7-highspeed-3.6-integration-path.md`。
- 它不覆盖或删除更广的 W8 hardening theme，只是先把一个明确可收口的 local-primary real-adapter seam 单独落地。
- 本 pack 完成后，后续 successor 可以再回到：
  - ingress auth / signature hardening
  - queue governance / operator controls
  - delivery policy hardening
  - broader model/runtime governance
