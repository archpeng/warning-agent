# warning-agent integration rollout evidence baseline

- status: `active-ssot`
- scope:
  - `W6.S4a` operator-visible rollout evidence
  - webhook readiness evidence
  - runtime machine-readable rollout evidence sidecar
- last_updated: `2026-04-20`

## 1. Current truth

`warning-agent` 现在对当前 external integration surfaces 提供两个直接可读的 evidence surface：

1. operator readiness surface：`GET /readyz`
2. runtime/webhook evidence sidecar：`integration-rollout-evidence.v1`

这两个 surface 共同覆盖：

- outcome admission
- delivery env gate
- provider runtime gate

## 2. Operator readiness surface

`GET /readyz` 现在除了原有基础 checks 外，还返回：

- `integration_baseline.schema_version = integration-rollout-baseline.v1`
- `integration_baseline.operator_paths`
- `integration_baseline.outcome_admission`
- `integration_baseline.delivery_bridge`
- `integration_baseline.provider_runtime`

operator 现在可以直接看到：

- `/outcome/admit` 的 receipt contract truth
- `adapter-feishu` 当前是 `ready` 还是 `missing_env`
- `local_primary` / `cloud_fallback` real-adapter gate 当前是：
  - `smoke_default`
  - `missing_env`
  - `ready`

## 3. Runtime / webhook evidence sidecar

每次 runtime execution 持久化后，现在会额外写出：

- `rollout_evidence/<packet_id>.integration-rollout-evidence.json`

schema：

- `schema_version = integration-rollout-evidence.v1`

当前 sidecar 至少包含：

- `packet_id`
- `decision_id`
- `report_id`
- `generated_at`
- `integration_baseline`

这意味着：

- webhook receipt 的 `runtime.rollout_evidence_path` 可直接指向 machine-readable proof
- runtime summary 的 `rollout_evidence_path` 可直接作为 `W6.RV1` 输入证据

## 4. Honest semantics

当前 baseline 的含义不是 “production rollout completed”，而是：

1. outcome admission surface 已 operator-visible
2. delivery env gate truth 已 operator-visible
3. provider runtime gate truth 已 operator-visible
4. runtime/webhook path 可写出 closeout-ready machine evidence

它不表示：

- multi-env deployment ready
- secret-manager rollout ready
- remote vendor production cutover complete

## 5. Expected operator reading

### delivery bridge

- `env_gate_state = missing_env`
  - 表示当前 live vendor seam 已存在，但环境未满足，dispatch 应保持 deferred / non-live truth
- `env_gate_state = ready`
  - 表示当前 env seam 满足，可进入 local-proof live bridge path

### provider runtime

- `gate_state = smoke_default`
  - 默认 smoke truth 仍在生效
- `gate_state = missing_env`
  - operator 已 opt-in，但 env contract 未满足；runtime 必须 fail closed
- `gate_state = ready`
  - env seam 已满足；只有在 runtime client/provider 也存在时，才允许进入 local-proof real adapter path

## 6. Governing files

- `app/integration_evidence.py`
- `app/receiver/alertmanager_webhook.py`
- `app/runtime_entry.py`
- `app/delivery/runtime.py`
- `app/delivery/env_gate.py`
- `app/investigator/provider_boundary.py`
- `tests/test_integration_evidence.py`
