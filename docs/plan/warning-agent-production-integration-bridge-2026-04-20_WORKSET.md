# warning-agent production integration bridge workset

- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- plan_class: `execution-plan`
- status: `in_progress`
- queue_mode: `strict-serial`
- active_wave: `wave-4 / W6 rollout evidence hardening`
- active_slice: `W6.S4a integration observability + rollout evidence baseline`
- last_updated: `2026-04-20`

## Completed slices

### `W6.S1a` — external outcome admission API baseline

- state: `completed`
- review verdict: `accept`
- verification:
  - targeted tests + direct smoke + `uv run pytest` + `uv run ruff check app tests scripts`

### `W6.S1b` — durable outcome receipt + feedback refresh glue

- state: `completed`
- review verdict: `accept`
- verification:
  - targeted outcome tests → `8 passed`
  - direct smoke via `POST /outcome/admit` → durable receipt evidence landed
  - `uv run pytest` → `132 passed`
  - `uv run ruff check app tests scripts` → pass

### `W6.S2a` — live delivery adapter contract + env config seam

- state: `completed`
- review verdict: `accept`
- verification:
  - targeted delivery/env-gate tests → `20 passed`
  - direct proof:
    - env missing → `deferred`
    - env ready → `queued` + bridge payload snapshot materialized
  - `uv run pytest` → `142 passed`
  - `uv run ruff check app tests scripts` → pass

### `W6.S2b` — first vendor delivery smoke bridge

- state: `completed`
- landed:
  - `app/delivery/bridge_result.py`
  - `app/delivery/http_client.py`
  - `app/delivery/runtime.py` real POST bridge writeback
  - `tests/test_delivery_adapter_feishu.py`
  - `tests/test_runtime_entry.py`
  - `tests/test_alertmanager_webhook.py`
- review verdict: `accept`
- verification:
  - `uv run pytest tests/test_delivery_adapter_feishu.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py` → `22 passed`
  - direct sibling-repo harness smoke:
    - warning-agent replay path POSTed to `adapter-feishu /providers/webhook`
    - delivery record ended `status=delivered`, `response_code=202`, `provider_status=delivered`
    - adapter harness log confirmed delivery
  - `uv run pytest` → `146 passed`
  - `uv run ruff check app tests scripts` → pass

### `W6.S3a` — real provider adapter contract freeze

- state: `completed`
- landed:
  - `configs/provider-boundary.yaml` smoke + real_adapter contract freeze
  - `app/investigator/provider_boundary.py` structured boundary loader + validation
  - `configs/escalation.yaml` smoke model naming freeze
  - `app/investigator/local_primary.py` explicit `local_primary_*` boundary notes
  - `app/investigator/fallback.py` explicit degraded local fail-closed boundary notes
  - `app/investigator/cloud_fallback.py` explicit `cloud_fallback_*` boundary notes
  - `docs/warning-agent-provider-boundary.md`
- review verdict: `accept`
- verification:
  - `uv run pytest tests/test_provider_boundary.py tests/test_fallback.py tests/test_cloud_fallback.py tests/test_investigator_router.py tests/test_configs.py` → `14 passed`
  - local contract/config proof:
    - `load_provider_boundary_config()` printed both providers' `mode / smoke / real_adapter / enabled_env` truth without runtime invocation
  - `uv run pytest` → `146 passed`
  - `uv run ruff check app tests scripts` → pass

### `W6.S3b` — provider runtime glue + fail-closed rollout gate

- state: `completed`
- landed:
  - `app/investigator/provider_boundary.py` real-adapter gate resolution
  - `app/investigator/local_primary.py` env-gated real-adapter runtime seam
  - `app/investigator/cloud_fallback.py` env-gated real-adapter runtime seam + explicit fail-closed gate behavior
  - `docs/warning-agent-provider-boundary.md` runtime-gated boundary truth
  - `tests/test_provider_boundary.py`
  - `tests/test_local_primary.py`
  - `tests/test_cloud_fallback.py`
  - `tests/test_investigation_runtime.py`
  - `tests/test_live_investigation.py`
  - `tests/test_live_runtime_entry.py`
- review verdict: `accept`
- verification:
  - `uv run pytest tests/test_provider_boundary.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_live_investigation.py tests/test_live_runtime_entry.py` → `21 passed`
  - local runtime-gate proof:
    - `resolve_real_adapter_gate(...)` produced `smoke_default` and `ready` states for both providers
  - `uv run pytest` → `151 passed`
  - `uv run ruff check app tests scripts` → pass

## Active slice

### `W6.S4a` — integration observability + rollout evidence baseline

- owner: `execute-plan`
- state: `ready`
- goal:
  - 把 outcome admission、delivery env gate、provider runtime gate 收敛成 operator-visible health/readiness/evidence baseline
  - 让 webhook/runtime/operator proof surfaces 能直接反映当前 integration bridge truth
  - 为 `W6.RV1` reality audit 提供 closeout-ready rollout evidence

### Governing truth for this slice

- `docs/warning-agent-provider-boundary.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
- current repo surfaces:
  - `app/receiver/alertmanager_webhook.py`
  - `app/runtime_entry.py`
  - `app/delivery/runtime.py`
  - `app/investigator/provider_boundary.py`
  - `tests/test_alertmanager_webhook.py`
  - `tests/test_runtime_entry.py`
  - `tests/test_live_runtime_entry.py`

### Primary surfaces

- `app/receiver/alertmanager_webhook.py`
- `app/runtime_entry.py`
- `app/delivery/runtime.py`
- `app/investigator/provider_boundary.py`
- 必要时：
  - `docs/warning-agent-provider-boundary.md`
  - operator-facing runbook / evidence doc surface
- tests:
  - `tests/test_alertmanager_webhook.py`
  - `tests/test_runtime_entry.py`
  - `tests/test_live_runtime_entry.py`
  - `tests/test_provider_boundary.py`
  - 必要时新增 operator-readiness / rollout-evidence tests

### Deliverable

一个最小但真实的 rollout-evidence baseline 修复包，满足：

1. operator-facing health/readiness surfaces 能反映新的 external integration truth。
2. delivery env gate 与 provider runtime gate 的当前状态有 operator-visible evidence，而不只存在于代码内部。
3. runtime/webhook proof surfaces 能给 `W6.RV1` 提供 closeout-ready evidence。
4. 仍保持 S4a evidence-hardening scope，不进入 multi-env deployment platform 或 broad observability program。

### Expected verification

1. targeted tests
   - `uv run pytest tests/test_alertmanager_webhook.py tests/test_runtime_entry.py tests/test_live_runtime_entry.py tests/test_provider_boundary.py`
   - 必要时新增 operator-readiness / rollout-evidence tests
2. targeted smoke
   - local webhook/runtime readiness proof only；S4a 不进入 multi-env deployment platform
3. hygiene
   - `uv run ruff check app tests scripts`

### Done-when boundary

只有在以下同时成立时，`W6.S4a` 才能 claim done：

- operator-visible health/readiness 已覆盖新的 external integration surfaces
- delivery env gate / provider runtime gate 有可复用 evidence surface
- targeted tests 与 targeted local proof 全部通过
- 没有把 work 扩张到 multi-env deployment、secret manager、dashboard program 或 broad platform build-out

### Stop condition

命中以下任一项必须停止并回到 `plan-creator` 或至少暂停当前 slice：

- 为了给出最小 rollout evidence，必须依赖远端 deployment orchestration 或 secret-manager rollout
- evidence baseline 被证明离不开新的平台级 observability program
- 改动自然溢出到 `W6.RV1` reality audit 或 successor W7 work

### Next handoff after done

- `W6.RV1` — reality audit + W7 replan input

## Queued slices

| Order | Slice | Summary | State |
|---|---|---|---|
| 8 | `W6.RV1` | reality audit + W7 replan input | `queued` |

## Boundary rule

- 当前 workset 只允许执行 `W6.S4a`。
- 若 execution 过程中出现多个同级主方案，必须先停下，不得让本 workset 退化成 changelog dump。
- 在 `W6.S4a` 完成前，不得提前 claim `W6.RV1` 已开始。
- `W6.S3a` / `W6.S3b` provider truth 已 landed；当前 slice 不得回退重做 provider contract/runtime gate，而应把证据面补齐到 operator-visible baseline。
