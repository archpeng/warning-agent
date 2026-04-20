# warning-agent warning-plane production stability plan

- plan_id: `warning-agent-warning-plane-production-stability-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- predecessor_plan: `warning-agent-minimax-local-primary-real-adapter-2026-04-20`
- carried_input_1: `docs/plan/warning-agent-minimax-local-primary-successor-replan-input-2026-04-20.md`
- carried_input_2: `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`
- last_updated: `2026-04-20`

## 1. Goal

在以下事实都已经 landed 之后：

- `P3-P5` local analyzer / investigator / cloud-fallback baseline 已闭合
- `W7` governed Signoz warning ingress + durable queue / worker / readiness truth 已闭合
- `MM` local-primary real adapter seam 已闭合到 runtime auto-wiring

本 pack 现在按用户新的模型拓扑要求重新收敛为：

> 让 `warning-agent` 在**当前既有架构边界内**，把 `3.6 Investigation` 收成一个 production-operable stable output 形态：
>
> - `local_primary` = **Gemma4 26B** 本地常驻调查模型
> - **开机预热一次**，服务常驻，不把冷启动暴露给每次 warning
> - `warning-agent` 只在 `3.6 Investigation` 真正需要时调用它
> - 如果本地模型 `not ready` / degraded，再按显式策略：
>   - **退化到 cloud fallback**，或
>   - **进入队列等待恢复**
> - `cloud_fallback` = **Neko API 上的 OpenAI GPT-5.4 xhigh**
>
> 也就是把系统语义固定为：
>
> - 正常情况：无冷启动感知
> - 异常情况：退化到 fallback 或排队等待恢复

这里的重点不是再发明一条新架构，也不是把 repo 扩成平台，而是把当前残余 gap 压成一组 proof-carrying、可审计、可 fail-closed 的模型运行时治理 slices。

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-provider-boundary.md`
- `docs/warning-agent-integration-rollout-evidence.md`
- `docs/debt/warning-agent-full-flow-and-production-gap.md`
- `docs/analyse/warning-agent-local-first-investigation-path.md`
- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_CLOSEOUT.md`
- `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`
- `docs/plan/warning-agent-minimax-local-primary-real-adapter-2026-04-20_CLOSEOUT.md`
- `docs/plan/warning-agent-minimax-local-primary-successor-replan-input-2026-04-20.md`

当前 repo reality 的高信号代码面：

- `app/runtime_entry.py`
- `app/main.py`
- `app/integration_evidence.py`
- `app/investigator/provider_boundary.py`
- `app/investigator/local_primary.py`
- `app/investigator/local_primary_openai_compat.py`
- `app/investigator/cloud_fallback.py`
- `app/live_local_primary_smoke.py`
- `app/receiver/signoz_ingress.py`
- `app/receiver/signoz_queue.py`
- `app/receiver/signoz_worker.py`
- `app/storage/signoz_warning_store.py`
- `app/delivery/runtime.py`
- `app/feedback/*`
- `configs/escalation.yaml`
- `configs/provider-boundary.yaml`
- `scripts/run_local_analyzer_benchmark.py`
- `scripts/run_local_primary_benchmark.py`
- `scripts/run_cloud_fallback_benchmark.py`

## 3. Current project analysis

### 3.1 What is already true

当前 repo 已经证明：

1. warning-plane 主链路已经存在：Signoz warning / Alertmanager / replay -> evidence -> packet -> local analyzer -> optional investigation -> report -> feedback。
2. `3.5 first-pass` 已 landed 为 canonical `local-analyzer-decision.v1`，runtime 已真正消费 retrieval hits。
3. `3.6 investigation` 已 landed 为 canonical `investigation-result.v1`，默认 `local-primary`，必要时 `cloud-fallback`。
4. governed Signoz ingress、durable admission、queue/worker boundary、`/readyz` operator truth 已落地。
5. local-primary real adapter seam 已落地到：
   - explicit env contract
   - bounded OpenAI-compatible client
   - runtime auto-wiring
   - fail-closed fallback
6. cloud fallback 的角色已经清楚：
   - 只处理 local-primary 未收敛 / 低置信 / unresolved case
   - 只消费 compressed handoff + bounded refs
7. 全 repo 当前已有 regression / lint baseline，且 machine-readable control-plane 已稳定工作。

### 3.2 What is still missing under the new user requirements

在用户现在要求的模型拓扑下，剩余 gap 已经具体化为：

1. `local_primary` 当前仍是 generic local path；尚未冻结成 **Gemma4 26B resident service** 的角色与 readiness contract。
2. `cloud_fallback` 当前仍是 generic smoke + future adapter；尚未冻结成 **Neko API / OpenAI GPT-5.4 xhigh** 的真实 fallback 身份。
3. 当前 `local_primary` 预算仍偏保守；不符合“本地 26B 作为主调查面”的语义。
4. 当前 runtime 仍缺少：
   - 开机预热一次
   - 服务常驻
   - local ready / not-ready / degraded 明确状态
   - local not ready 时的 **fallback-or-queue** 显式策略
5. 当前 `3.5 -> 3.6` 的 acceptance gates 还没有围绕新的主次模型分工重新校准。
6. 当前 `/readyz` / rollout evidence 还没有诚实表达：
   - resident local service readiness
   - prewarm status
   - fallback eligibility
   - queue-wait policy state

## 4. Architectural invariants and code norms

本 pack 必须遵守当前 repo 已形成的架构与代码规范：

1. **canonical contracts stay frozen**：
   - `incident-packet.v1`
   - `local-analyzer-decision.v1`
   - `investigation-result.v1`
   - `alert-report.v1`
   - `incident-outcome.v1`
2. **single runtime spine**：不得绕过 packet/decision/investigation/report 另长第二条产品主线。
3. **local-first investigator remains true**：`local_primary` 仍是默认 `3.6` provider；`cloud_fallback` 仍只在必要时使用。
4. **resident local semantics**：warning-agent 不应在每次 `3.6` 调用时临时拉起本地 26B；应把“开机预热一次、服务常驻、按需调用”当作显式设计约束。
5. **bounded evidence only**：不允许把 raw logs / trace trees 无边界塞进模型路径。
6. **fail-closed over pretend-live**：env 缺失、provider unavailable、resident service 不 ready、queue ambiguity、delivery ambiguity 都必须显式暴露。
7. **queue-or-fallback must be explicit**：本地模型不 ready 时，必须由 machine-readable policy 决定是：
   - 退化到 `cloud_fallback`
   - 进入队列等待恢复
   不允许隐式卡住或会话内拍脑袋。
8. **operator-visible truth first**：所有生产稳定性 claim 都应能从 `/readyz`、rollout evidence、artifacts、tests、runbooks 中直接复核。
9. **config + typed runtime style**：继续沿用当前 repo 的 `configs/*.yaml` + `dataclass` / `TypedDict` / `Protocol` 风格，而不是引入重型框架。
10. **proof-carrying tests**：每个 slice 都先补 targeted proof，再落实现；最终仍要回到 `uv run pytest` + `uv run ruff check app tests scripts`。
11. **no platform creep**：不得把 repo 推向 generic multi-provider SDK、workflow engine、multi-agent orchestration、observability suite。

## 5. Scope

### In scope

- freeze `local_primary = Gemma4 26B resident local service` as the default 3.6 provider contract
- freeze `cloud_fallback = Neko API / OpenAI GPT-5.4 xhigh` as the bounded fallback provider contract
- greatly expand local-primary investigation budget to match the new 26B role
- add boot-prewarm / service-resident / ready-not-ready contract for local-primary
- define explicit `fallback or queue-wait` semantics when the local resident model is not ready
- real provider rollout operator truth and rollback/disable governance
- 3.5 -> 3.6 acceptance gates under the new model split
- queue / ingress / delivery / feedback governance updates needed to support the new runtime semantics
- end-to-end operator evidence pack and production-stability runbook
- closeout / audit / residual freeze for the current architecture boundary

### Out of scope

- changing canonical runtime contracts
- replacing local analyzer with a prompt-heavy model runtime
- making cloud fallback the default plane
- building a generic provider framework or orchestration platform
- promising deployment/orchestration machinery beyond the current repo boundary unless evidence truly supports it
- remediation / automatic execution / incident platform features

## 6. Solution outline

本方案围绕四条收口主线推进：

### A. Model role freeze line

先把模型职责彻底冻结：

- `local_primary` = resident Gemma4 26B, main 3.6 investigator
- `cloud_fallback` = Neko API GPT-5.4 xhigh, sparse fallback only

### B. Resident local runtime line

把 local-primary 从 generic seam 推进为：

- boot prewarm once
- resident service
- explicit ready / not-ready / degraded truth
- no per-warning cold-start semantics

### C. Fallback / queue policy line

把 local not-ready 情况显式化：

- when to fallback immediately
- when to queue and wait for recovery
- what `/readyz` and rollout evidence should say

### D. Acceptance / governance line

把新的模型分工、预算、稳定性 gates、operator runbook、warning-plane governance 收成 production-stability evidence pack，并在 closeout 前做 reality audit。

## 7. Wave decomposition

### wave-1 / PS model topology and contract freeze

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `PS.S1a` model-role split + resident runtime contract freeze | `configs/escalation.yaml`、`configs/provider-boundary.yaml`、`app/investigator/provider_boundary.py`、`docs/warning-agent-provider-boundary.md`、`docs/warning-agent-integration-rollout-evidence.md`、targeted tests | provider roles、model identities、ready/not-ready semantics、fallback-or-queue policy 都被明确写成 machine-readable contract；targeted tests pass | 不 claim live rollout complete；不改 canonical contracts |
| `PS.S1b` budget expansion + rollout evidence contract alignment | `configs/escalation.yaml`、`app/integration_evidence.py`、`docs/*runbook*`、targeted tests | greatly expanded local-primary budget 与 operator-visible readiness/evidence fields 对齐；downstream runtime slices 不再有预算语义歧义 | 不实现 boot prewarm；不提前改 runtime lifecycle |

### wave-2 / PS resident local runtime and fallback materialization

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `PS.S2a` Gemma4 26B resident local-primary lifecycle | `app/main.py`、`app/runtime_entry.py`、`app/investigator/local_primary.py`、必要时新的 local runtime health/warmup surface、targeted tests | boot prewarm once、resident service、warning-agent only calls it when 3.6 is needed；ready/not-ready/degraded semantics test-backed | 不把 warning-agent 扩成 full model-serving platform |
| `PS.S2b` local not-ready -> fallback or queue semantics | `app/runtime_entry.py`、`app/receiver/signoz_queue.py`、`app/receiver/signoz_worker.py`、`app/integration_evidence.py`、targeted tests | local not-ready path 会按显式 policy 退化到 cloud fallback 或进入队列等待恢复；operator truth 可见 | 不把 queue 变成 generic job orchestrator |
| `PS.S2c` cloud fallback conversion to Neko GPT-5.4 xhigh | `app/investigator/cloud_fallback.py`、`configs/provider-boundary.yaml`、`configs/escalation.yaml`、targeted tests / smoke docs | cloud_fallback 的 real adapter / model identity / handoff contract 都对齐到 Neko API GPT-5.4 xhigh；bounded handoff 仍成立 | 不让 cloud 重新变成默认 plane |
| `PS.S2d` 3.5 -> 3.6 stability gates under the new split | `app/analyzer/benchmark.py`、`app/investigator/benchmark.py`、`scripts/run_local_analyzer_benchmark.py`、`scripts/run_local_primary_benchmark.py`、`scripts/run_cloud_fallback_benchmark.py`、benchmark tests | `investigation_candidate_rate`、`local_primary_invocation_rate`、fallback ratio、queue-wait ratio、latency/degraded validity 都有 accepted evidence | 不把 first-pass 重写成 prompt-heavy runtime |

### wave-3 / PS operator governance and acceptance

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `PS.S3a` warning-plane governance update for the new model topology | `app/receiver/signoz_ingress.py`、`app/receiver/signoz_queue.py`、`app/delivery/runtime.py`、`app/feedback/*`、runbooks/tests | ingress / queue / delivery / feedback truth 现在能诚实表达 resident-local / fallback / queue-wait semantics | 不扩成 deployment/orchestration platform |
| `PS.S3b` end-to-end production evidence pack + operator runbook | new docs / evidence pack / smoke notes / benchmark artifacts | operator 可以不依赖会话上下文复核：模型角色、预算、ready/not-ready policy、fallback policy、rollback policy | 不 claim beyond current architecture evidence |
| `PS.RV1` reality audit + residual freeze | closeout doc、successor residual note、control-plane closeout | verdict=`accept` or `accept_with_residuals`；remaining residuals honest frozen | 不把未验证内容混进“production-ready completed” |

## 8. Validation ladder

本 pack 默认验证顺序固定为：

1. 当前 active slice 的 targeted tests / targeted docs proof
2. 若 slice 涉及 provider contract / budget contract：
   - `uv run pytest tests/test_provider_boundary.py tests/test_integration_evidence.py tests/test_signoz_warning_readiness.py`
3. 若 slice 涉及 resident local runtime：
   - targeted local-primary tests / runtime tests / env-opt smoke
4. 若 slice 涉及 benchmark gates：
   - `uv run python scripts/run_local_analyzer_benchmark.py`
   - `uv run python scripts/run_local_primary_benchmark.py`
   - `uv run python scripts/run_cloud_fallback_benchmark.py`
5. `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py`
6. `uv run pytest`
7. `uv run ruff check app tests scripts`

没有 matching evidence，不得 claim slice done。

## 9. Closeout rule

本 pack 只能在以下同时成立时 closeout：

- `local_primary = Gemma4 26B resident investigator` 的角色、预算、prewarm、readiness truth 已显式冻结并有代码/测试证据
- `cloud_fallback = Neko API GPT-5.4 xhigh` 的角色与 handoff boundary 已显式冻结并有代码/测试证据
- local not-ready path 具备 machine-readable `fallback or queue-wait` policy，而不是隐式行为
- `3.5 -> 3.6` coupling 在新的模型分工下有 accepted gates，而不是只有“逻辑接通”
- `/readyz` 与 rollout evidence 可以诚实表达当前 mode / auth / queue / local-ready / fallback / delivery truth
- operator 可以依赖 runbook 与 evidence pack 做 enable / disable / rollback / triage
- `PS.RV1` reality audit 通过
- remaining residuals 已显式冻结到 successor，而不是藏在“production-ready”表述里

## 10. Mandatory replan triggers

命中任一项必须停下并 replan：

1. Neko API 上的 GPT-5.4 xhigh 被证明并非当前可接入的 OpenAI-compatible path。
2. Gemma4 26B resident requirement 被证明必须依赖超出当前 repo boundary 的平台化 serving/orchestration 才能落地。
3. 为了完成当前目标必须修改 canonical packet / decision / investigation contracts。
4. local not-ready queue-wait semantics 被证明需要 generic workflow/job platform。
5. 为了完成当前 goal 必须把产品扩成 remediation / workflow / multi-agent system。
6. 没有真实可访问的 target environment，却又试图 claim resident/local or cloud live rollout completed。

## 11. Exit / successor rule

- 本 pack 现在把目标明确收到：`Gemma4 26B resident local-primary + Neko GPT-5.4 xhigh cloud-fallback` 的 production-operable stable output。
- 它不会覆盖此前已 closeout 的 W7 / MM truth，而是把这些 truth 当作前置已知条件。
- 本 pack 完成后，如仍要继续推进更大范围的 multi-env platform / distributed queue / external serving infra work，应进入新的 successor planning，而不是继续在当前 pack 中扩 scope。
