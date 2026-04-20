# warning-agent architecture clarity optimization plan

- plan_id: `warning-agent-architecture-clarity-optimization-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- predecessor_plan: `warning-agent-warning-plane-production-stability-2026-04-20`
- carried_input_1: `docs/plan/warning-agent-warning-plane-production-stability-successor-replan-input-2026-04-20.md`
- carried_input_2: `docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`
- last_updated: `2026-04-20`

## 1. Goal

在 `warning-agent-warning-plane-production-stability-2026-04-20` 已经 closeout、且当前 runtime/provider topology 已稳定之后，新的目标不是继续扩大产品边界，而是：

> 对当前 repo 做一次 **代码架构清晰度优化**，重点收口 `3.5 first-pass` 与 `3.6 investigation` 的模块边界、文件职责、依赖方向与 future-learning groundwork，
> 让后续优化能在 **不重开 canonical contracts、不引入过度工程化、不把 repo 推向 generic platform** 的前提下，清晰、可验证、可连续自动推进。

这里的重点是：

- 让 `3.5` 更像一个可学习、可替换、可比较的 triage surface
- 让 `3.6` 更像一个由明确 runtime policy 驱动的 investigation surface
- 先把代码结构收干净，再考虑更深的学习优化
- 明确采纳 future note 的核心路线：
  - `keep the shell`
  - `learn the policies`
  - `extract later`

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-provider-boundary.md`
- `docs/warning-agent-warning-plane-production-stability-runbook.md`
- `docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_CLOSEOUT.md`
- `docs/plan/warning-agent-warning-plane-production-stability-successor-replan-input-2026-04-20.md`
- `docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`

当前 repo reality 的高信号代码面：

- `app/analyzer/*`
- `app/investigator/*`
- `app/runtime_entry.py`
- `app/main.py`
- `app/packet/*`
- `app/receiver/*`
- `app/integration_evidence.py`
- `app/delivery/*`
- `app/feedback/*`
- `configs/escalation.yaml`
- `configs/provider-boundary.yaml`
- `tests/test_investigation_runtime.py`
- `tests/test_local_primary.py`
- `tests/test_cloud_fallback.py`
- `tests/test_investigator_benchmark.py`
- `tests/test_bootstrap.py`
- `tests/test_autopilot_control_plane.py`

## 3. Current project analysis

### 3.1 What is already healthy

当前 repo 已经具备这些重要前提：

1. canonical contracts 已冻结且仍健康：
   - `incident-packet.v1`
   - `local-analyzer-decision.v1`
   - `investigation-result.v1`
   - `alert-report.v1`
   - `incident-outcome.v1`
2. `3.5 -> 3.6` 的产品主链已经可运行、可测试、可 benchmark。
3. `local_primary` / `cloud_fallback` 的 provider boundary、resident lifecycle、abnormal-path truth、operator-visible evidence 已 landed。
4. warning-plane queue / delivery / feedback governance 已 landed，full regression 与 lint 当前通过。
5. runtime shell 已经够稳定，当前主要问题不再是“功能接不通”，而是“代码边界还不够清楚”。

### 3.2 What is still structurally unclear

当前 repo 的主要结构性问题已经收敛成下面几类：

1. **hotspot files too thick**：
   - `app/investigator/local_primary.py`
   - `app/investigator/cloud_fallback.py`
   - `app/runtime_entry.py`
   - `app/storage/signoz_warning_store.py`
   - `app/collectors/evidence_bundle.py`
2. **runtime / benchmark / training glue 仍偏混杂**：
   - `app/analyzer/*` 同时承载 runtime scorer、training、benchmark、replay glue
   - `app/investigator/*` 同时承载 runtime providers、fallback policy、handoff/compression、benchmark glue
3. **cross-layer imports 仍不够干净**：
   - `packet` 仍反向借用 `receiver` 类型
   - `runtime_entry` 汇聚了过多 family 依赖
   - package `__init__` 仍混合 export runtime 与 benchmark/training surfaces
4. **future-learning groundwork 仍主要停留在文档里**：
   - `SidecarAssistPacket`
   - `DecisionAuditRecord`
   - `ActionTrace`
   - `InvestigationEvidencePack`
   - `CompressedInvestigationBrief`
   目前还没有在代码中形成稳定、最小、不过度的 internal objects。

### 3.3 What this pack must achieve

本 pack 不是做新产品能力，而是做下面三件事：

1. 让代码结构与已经冻结的产品/contract truth 对齐。
2. 让 `3.5` 与 `3.6` 的优化对象更清楚地落到：
   - state-lite / internal objects
   - policy surfaces
   - benchmark / compare surfaces
3. 为 future note 准备最小必要基础，而不是提前重构成 `warning-core` 或 generic policy engine。

## 4. Architectural invariants and code norms

本 pack 必须继续遵守当前 repo 已形成的架构与代码规范：

1. **canonical contracts stay frozen**：
   - `incident-packet.v1`
   - `local-analyzer-decision.v1`
   - `investigation-result.v1`
   - `alert-report.v1`
   - `incident-outcome.v1`
2. **keep the shell**：不重开 ingress / packet / report / delivery / feedback 这些外层 runtime shell。
3. **provider topology stays true**：
   - `local_primary` 仍是默认 `3.6` provider
   - `cloud_fallback` 仍只做 sparse fallback
4. **no platform creep**：不得把 repo 推向：
   - generic multi-provider SDK
   - workflow / orchestration platform
   - online learning runtime
   - `warning-core` 提前抽离
5. **minimal internal objects first**：只引入支持 clarity / replay / compare / attribution 的最小 internal objects，不一次性扩成 `app/state/*` / `app/policies/*` 大框架。
6. **proof-carrying refactor**：每个 slice 都必须给出 targeted verification，不能只做“移动代码更好看”。
7. **autopilot-compatible control plane**：本 pack 的 source/machine docs 必须持续保持 parser-compatible。
8. **avoid semantic drift while refactoring**：结构优化优先保持 runtime semantics 与 benchmark gates 不变；若必须调整行为，只允许做与切分直接相关的最小等价修正。

## 5. Scope

### In scope

- 为 `3.5` 明确 runtime / benchmark / training / assist / audit 的模块边界
- 为 `3.6` 明确 local resident lifecycle / abnormal-path policy / cloud brief+client+mapping 的模块边界
- 收口跨层依赖与 import direction，尤其是 packet / receiver / runtime glue
- 将 future note 里的最小 internal learning objects 以 **不过度工程化** 的方式做准备
- 更新 docs / tests / benchmarks / runbook，使后续执行不依赖会话记忆
- 形成 proof-carrying refactor slices，供 `execute-plan` 严格串行推进

### Out of scope

- 修改 canonical contracts
- 重写当前 model topology 或 provider semantics
- 引入 online learning、auto-promotion、policy engine runtime
- 把 repo 迁移到 `warning-core`
- 引入分布式 orchestration / queue / serving platform
- 把本 pack 扩成性能调优 / live rollout / infra hardening family

## 6. Solution outline

本 pack 围绕四条主线推进：

### A. Boundary freeze + hotspot inventory

先把当前结构优化的 guardrails 写死：

- 什么可以拆
- 什么不能动
- 哪些是 hotspot
- 哪些 future-note internal objects 只允许以最小形态进入

### B. `3.5` analyzer clarity line

把 `3.5` 从“runtime scorer + benchmark/training/replay glue 混在一个 family”收成：

- runtime scoring surface
- training / benchmark surface
- minimal assist / audit surface

### C. `3.6` investigator clarity line

把 `3.6` 从“厚 provider 文件”收成：

- local resident lifecycle / abnormal policy / provider adapter seams
- cloud brief / guard / transport / mapping seams
- execution spine imports 更干净

### D. Minimal future-learning groundwork line

只做对 future note 真正必要的准备：

- passive internal objects
- attribution / compare-friendly traces
- docs / benchmark surfaces 对齐

不提前长出新的 runtime platform。

## 7. Wave decomposition

### wave-1 / guardrails and seam inventory

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `AC.S1a` architecture clarity guardrail freeze + hotspot map | `docs/warning-agent-architecture.md`、`docs/warning-agent-provider-boundary.md`、`docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`、必要时新增 architecture-clarity design doc、targeted tests | current refactor scope、protected surfaces、hotspots、no-overengineering rules 明确落地；machine control-plane remains aligned | 不开始大规模代码搬移；不提前引入 generic state/policy trees |
| `AC.S1b` dependency hygiene target map + runtime/benchmark ownership inventory | `app/analyzer/__init__.py`、`app/investigator/__init__.py`、`app/runtime_entry.py`、`app/packet/*`、`tests/*`、docs inventory | 当前 import debt、runtime vs benchmark ownership、planned move map 和 boundary test surfaces 明确可执行 | 不把 inventory slice 偷偷变成 full refactor |

### wave-2 / `3.5` analyzer modular clarity

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `AC.S2a` `3.5` runtime/training boundary cleanup | `app/analyzer/runtime.py`、`app/analyzer/fast_scorer.py`、`app/analyzer/trained_scorer.py`、`app/analyzer/calibrate.py`、`app/analyzer/benchmark.py`、tests | runtime scorer path 与 training/benchmark glue 的 ownership 更清楚，decision contract 不变，existing analyzer/benchmark tests pass | 不重写 scorer logic；不改变 external decision fields |
| `AC.S2b` `3.5` assist/audit groundwork | `app/analyzer/*`、`app/feedback/compare.py`、`tests/test_fast_scorer.py`、`tests/test_trained_scorer.py`、新的 targeted tests | `SidecarAssistPacket` / `DecisionAuditRecord` 以 minimal internal form 落地或具备稳定 seam，仍不重开 canonical decision contract | 不把 `3.5` 变成第二条聊天 agent runtime |

### wave-3 / `3.6` investigator modular clarity

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `AC.S3a` `3.6` local-primary internal split | `app/investigator/local_primary.py`、`app/investigator/local_primary_openai_compat.py`、必要时新的 resident/abnormal/provider seam modules、targeted tests | resident lifecycle、abnormal-path policy、real-adapter construction 与 smoke behavior 的职责更清楚，existing local/runtime tests pass | 不改变 current provider semantics；不引入 serving platform assumptions |
| `AC.S3b` `3.6` cloud-fallback internal split | `app/investigator/cloud_fallback.py`、`app/investigator/cloud_fallback_openai_responses.py`、必要时新的 brief/guard/mapping modules、targeted tests | compressed handoff、guard logic、transport client、result mapping 的职责分开，cloud fallback semantics unchanged | 不把 cloud path 重构成 default plane 或 generic client SDK |
| `AC.S3c` execution spine and normalized-alert dependency hygiene | `app/runtime_entry.py`、`app/packet/builder.py`、`app/receiver/alertmanager_webhook.py`、`app/receiver/signoz_alert.py`、`app/integration_evidence.py`、tests | packet / receiver / runtime glue 的依赖方向更干净；bootstrap/runtime/receiver tests pass | 不在这一 slice 顺手改产品行为 |

### wave-4 / minimal future-note groundwork and alignment

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `AC.S4a` minimal internal learning objects + docs/benchmark alignment | `app/investigator/*`、`app/feedback/*`、`docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`、`docs/warning-agent-architecture.md`、benchmark/readme/runbook docs、targeted tests | `ActionTrace` / `InvestigationEvidencePack` / `CompressedInvestigationBrief` 的最小 groundwork 与 docs/benchmark surfaces 对齐，仍不引入 online learning or policy engine | 不扩成 full `app/state/*` / `app/policies/*` framework |
| `AC.RV1` reality audit + residual freeze | closeout doc、successor residual note、control-plane closeout | refactor pack verdict clear；remaining residuals honest frozen；next handoff explicit | 不把未落地的 future-learning ambition 混成“已完成” |

## 8. Validation ladder

本 pack 默认验证顺序固定为：

1. 当前 active slice 的 targeted proof
2. control-plane compatibility proof：
   - `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py`
3. 若 slice 涉及 `3.5` analyzer surfaces：
   - relevant `tests/test_fast_scorer.py`
   - `tests/test_trained_scorer.py`
   - `tests/test_benchmark.py`
   - `tests/test_investigator_benchmark.py` when coupling matters
4. 若 slice 涉及 `3.6` investigator surfaces：
   - `tests/test_local_primary.py`
   - `tests/test_cloud_fallback.py`
   - `tests/test_investigation_runtime.py`
   - `tests/test_live_runtime_entry.py`
   - `tests/test_live_investigation.py`
   - `tests/test_provider_boundary.py`
5. 若 slice 涉及 warning-plane spine / receiver / packet / runtime glue：
   - `tests/test_signoz_worker_runtime.py`
   - `tests/test_alertmanager_webhook.py`
   - `tests/test_signoz_queue_contract.py`
   - `tests/test_signoz_warning_readiness.py`
   - `tests/test_runtime_entry.py`
6. `uv run pytest`
7. `uv run ruff check app tests scripts`

没有 matching evidence，不得 claim slice done。

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. 为了做 clarity refactor 被迫修改 canonical contracts。
2. 任一 slice 需要提前引入新的 generic state/policy/runtime framework 才能继续。
3. 任一 slice 同时包含“结构优化 + 语义优化 + benchmark目标变化”三个主目标，无法保持 bounded。
4. current runtime semantics 在重构后无法被 targeted tests 等价证明。
5. 需要把当前工作迁移到 `warning-core` / 新 repo 才能继续。
6. current plan 被 scope creep 成 infra/platform work。

## 10. Closeout rule

本 pack 只能在以下同时成立时 closeout：

- `3.5` 的 runtime / training / benchmark / assist / audit seams 已比当前明显更清楚
- `3.6` 的 local-primary / cloud-fallback / execution-spine seams 已比当前明显更清楚
- 关键厚文件已经被收成更小、更单一职责的模块，或至少具备清晰的 ownership split
- future note 里最关键的 minimal internal groundwork 已有代码落点，而不是只留在文档愿景中
- full regression 与 lint 通过
- 仍然没有越过当前产品与架构边界
- `AC.RV1` reality audit 对“clarity uplift but no overengineering drift”给出 honest verdict

## 11. Exit / successor rule

- 本 pack 的目标是：**让 `warning-agent` 在当前 repo 内更容易继续做 `3.5/3.6` 学习优化，而不是立即做下一轮平台化迁移**。
- 本 pack 完成后，如要继续推进更深层的 policy compare / learning loop / extraction gate，必须新开 successor pack。
- 若未来要做 `warning-core` 抽离，只能在本 pack 之后、并且 internal objects / policy surfaces 已稳定时进行。