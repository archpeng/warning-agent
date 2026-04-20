# warning-agent production integration bridge status

- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- plan_class: `execution-plan`
- status: `in_progress`
- current_wave: `wave-4 / W6 rollout evidence hardening`
- current_step: `W6.S4a integration observability + rollout evidence baseline`
- last_updated: `2026-04-20`

## 1. Current truth

- `W5 production readiness foundation` 已 completed 并 closeout。
- closeout verdict：`accept_with_residuals`
- `W6.S1a` 已 completed，并在 reality audit 下被确认可 honest claim done。
- `W6.S1b` 已 completed，并已把 outcome admission receipt 从 immediate success envelope 收敛成更 durable 的 feedback evidence trail。
- `W6.S2a` 已 completed，并把首个 live vendor adapter seam 冻结为 `adapter-feishu` 的 env-gated local-proof contract。
- `W6.S2b` 已 completed，并把 `warning-agent -> adapter-feishu -> Feishu/Lark` 的 first vendor bridge 跑通到本地 harness smoke proof。
- `W6.S3a` 已 completed，并把 investigator plane 的 current smoke identity 与 future real adapter contract 明确切开。
- `W6.S3b` 已 completed，并把 `W6.S3a` 的 frozen real-adapter contract 真正接到 runtime gate：
  - default path 仍保持 smoke truth
  - env gate missing / client missing 时现在显式 fail closed
  - injected real adapter provider/client 已有 local-proof runtime path
  - `docs/warning-agent-provider-boundary.md` 已升级为 runtime-gated boundary SSOT
- `W6` 当前状态：`in_progress`，active slice 已切换为 `W6.S4a`。

## 2. Recently completed

### `W6.S3b` — provider runtime glue + fail-closed rollout gate

landed truth：

- 更新 `app/investigator/provider_boundary.py`
  - 新增 `ResolvedRealAdapterGate`
  - 新增 `resolve_real_adapter_gate(...)`
  - 现在能显式区分：`smoke_default` / `missing_env` / `ready`
- 更新 `app/investigator/local_primary.py`
  - `LocalPrimaryInvestigator` 现在会解析 real-adapter gate
  - gate ready 时可消费 injected `real_adapter_provider`
  - gate missing/client missing 时会显式抛出 runtime gate failure，交给 fail-closed fallback
- 更新 `app/investigator/cloud_fallback.py`
  - `CloudFallbackInvestigator` 现在会解析 real-adapter gate
  - gate ready 时可消费 injected `real_adapter_client`
  - gate missing/client missing 时会显式 fail closed 回 local result
  - real-adapter ready path 现在会把 env model name 写回 `investigation-result.v1`
- 更新 `docs/warning-agent-provider-boundary.md`
  - provider boundary doc 现在说明 runtime-gated semantics，而不再停留在 contract-only freeze
- 新增 / 更新 tests：
  - `tests/test_provider_boundary.py`
  - `tests/test_local_primary.py`
  - `tests/test_cloud_fallback.py`
  - `tests/test_investigation_runtime.py`
  - `tests/test_live_investigation.py`
  - `tests/test_live_runtime_entry.py`

review verdict：
- `accept`
- `next handoff: plan-creator`

verification：
- targeted tests:
  - `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_live_investigation.py tests/test_live_runtime_entry.py` → `21 passed`
- targeted local proof:
  - `resolve_real_adapter_gate(...)` proved `smoke_default` and `ready` states for both `local_primary` and `cloud_fallback` without remote rollout
- full regression:
  - `uv run pytest` → `151 passed`
- hygiene:
  - `uv run ruff check app tests scripts` → pass

### `W6.S3a` — real provider adapter contract freeze

landed truth：

- 更新 `configs/provider-boundary.yaml`
  - `local_primary` / `cloud_fallback` 现在都显式区分：
    - current `smoke` identity
    - frozen `real_adapter` contract
    - env-opt-in activation seam
- 更新 `app/investigator/provider_boundary.py`
  - 新增 structured smoke/real-adapter dataclasses
  - 新增 config validation，避免 boundary drift 静默进入 runtime
- 更新 `configs/escalation.yaml`
  - 当前 active smoke model name 冻结为：
    - `local-primary-smoke`
    - `cloud-fallback-smoke`
- 更新 `app/investigator/local_primary.py`
  - successful local investigations 现在会显式写出 current smoke vs future real adapter boundary notes
- 更新 `app/investigator/fallback.py`
  - degraded local fallback 现在会显式写出 `local_primary` contract notes + fail-closed target
- 更新 `app/investigator/cloud_fallback.py`
  - cloud fallback result / unavailable fallback 现在会显式写出 `cloud_fallback` contract notes + fail-closed target
- 更新 `docs/warning-agent-provider-boundary.md`
  - S3a contract SSOT 已说明 current smoke identity、future real adapter seam、activation env gate

review verdict：
- `accept`
- `next handoff: plan-creator`

verification：
- targeted tests:
  - `uv run pytest tests/test_provider_boundary.py tests/test_fallback.py tests/test_cloud_fallback.py tests/test_investigator_router.py tests/test_configs.py` → `14 passed`
- targeted local proof:
  - loaded `configs/provider-boundary.yaml` via `load_provider_boundary_config()` and printed both providers' `mode / smoke / real_adapter / enabled_env` truth without entering runtime invocation
- full regression:
  - `uv run pytest` → `146 passed`
- hygiene:
  - `uv run ruff check app tests scripts` → pass

## 3. Next step

next execution target：

- `W6.S4a` — integration observability + rollout evidence baseline

active objective：

- 把 outcome admission、delivery env gate、provider runtime gate 三类 external surfaces 收敛成 operator-visible health/readiness/evidence baseline
- 让 webhook/runtime/operator proof surfaces 能诚实显示当前 integration bridge 的 gate state，而不是只在代码里隐含
- 为 `W6.RV1` reality audit 提供 closeout-ready rollout evidence

expected proof：

- targeted tests:
  - `uv run pytest tests/test_alertmanager_webhook.py tests/test_runtime_entry.py tests/test_live_runtime_entry.py tests/test_provider_boundary.py`
  - 必要时新增 operator-readiness / rollout-evidence tests
- targeted smoke:
  - local webhook/runtime readiness proof only；S4a 不进入 multi-env deployment platform
- hygiene:
  - `uv run ruff check app tests scripts`

## 4. Blockers / risks

1. `W6.S4a` 若被证明离不开 multi-env deployment orchestration、secret manager 或远端环境 admission 才能给出最小 operator evidence，必须停止并 replan。
2. `W6.S4a` 必须复用当前真实 landed surfaces，不允许为了“看起来像 observability”而造第二套伪控制面。
3. 当前 workspace 仍是 dirty state；wave-4 execution 期间必须维持 strict-serial，不能把 `W6.RV1` 提前混入。
4. S4a 若自然溢出到 broader deployment platform / alert dashboard program，应停止并切回 successor planning，而不是在 W6 偷做 W7 工作。

## 5. Gate state

| gate | state | evidence |
|---|---|---|
| `W6.S1a` | `completed` | API route + receipt contract + artifact/metadata/retrieval proof + full regression |
| `W6.S1b` | `completed` | receipt contract now includes durable metadata/retrieval evidence trail + full regression |
| `W6.S2a` | `completed` | delivery contract split + adapter_feishu env seam + payload/env-gate proof + full regression |
| `W6.S2b` | `completed` | real POST bridge + local adapter-feishu harness smoke + full regression |
| `W6.S3a` | `completed` | smoke vs real adapter contract freeze + boundary notes + local contract proof + full regression |
| `W6.S3b` | `completed` | runtime gate resolution + injected real-adapter local proof + explicit fail-closed path + full regression |
| `W6.S4a` | `ready` | next gap is operator-visible rollout evidence for the landed external surfaces |
| `W6.RV1` | `pending` | 仅在全部 execution slices 完成后进入 reality audit |

## 6. Latest evidence

- wave-3 S3b final truth:
  - `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_live_investigation.py tests/test_live_runtime_entry.py` → `21 passed`
  - local gate proof via `resolve_real_adapter_gate(...)` showed:
    - default `smoke_default`
    - `local_primary` ready gate for `local_vllm_openai_compat`
    - `cloud_fallback` ready gate for `openai_responses_api`
  - `uv run pytest` → `151 passed`
  - `uv run ruff check app tests scripts` → pass
- governing truth for next slice:
  - `app/receiver/alertmanager_webhook.py`
  - `app/runtime_entry.py`
  - `app/delivery/runtime.py`
  - `app/investigator/provider_boundary.py`
  - `docs/warning-agent-provider-boundary.md`
  - `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
- code truth:
  - current active smoke path 仍诚实标识为 `local-primary-smoke` / `cloud-fallback-smoke`
  - real adapter seam 现在不再只是 config freeze，而是 env-gated runtime truth
  - 当前真实 gap 已切换到 `W6.S4a`：integration observability + rollout evidence baseline
