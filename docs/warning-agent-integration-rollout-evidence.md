# warning-agent integration rollout evidence baseline

- status: `active-ssot`
- scope:
  - `W6.S4a` operator-visible rollout evidence
  - `W7.S4a` governed Signoz warning-plane readiness truth
  - webhook readiness evidence
  - runtime machine-readable rollout evidence sidecar
- last_updated: `2026-04-20`

## 1. Current truth

`warning-agent` 现在对当前 external integration surfaces 提供两个直接可读的 evidence surface：

1. operator readiness surface：`GET /readyz`
2. runtime/webhook evidence sidecar：`integration-rollout-evidence.v1`

这两个 surface 现在共同覆盖：

- outcome admission
- governed Signoz warning ingress
- warning queue / backlog / dedupe / failure truth
- delivery env gate
- provider runtime gate

## 2. Operator readiness surface

`GET /readyz` 现在除了原有基础 checks 外，还返回：

- `integration_baseline.schema_version = integration-rollout-baseline.v1`
- `integration_baseline.operator_paths`
- `integration_baseline.outcome_admission`
- `integration_baseline.signoz_warning_plane`
- `integration_baseline.delivery_bridge`
- `integration_baseline.provider_runtime`

operator 现在可以直接看到：

- `/outcome/admit` 的 receipt contract truth
- `/webhook/signoz` 的 governed ingress contract truth
- Signoz ingress 当前是：
  - `auth_state = ready`
  - `auth_state = missing_env`
- Signoz queue 当前的：
  - `pending / processing / completed / failed / dead_letter / deduped`
  - `backlog_size`
  - `oldest_pending_age_sec`
  - `processing_failure_count`
  - `delivery_deferred_count`
  - `cloud_fallback_ratio`
- `adapter-feishu` 当前是 `ready` 还是 `missing_env`
- `local_primary` / `cloud_fallback` real-adapter gate 当前是：
  - `smoke_default`
  - `missing_env`
  - `ready`

## 3. Signoz warning-plane reading guide

### ingress auth

- `auth_state = missing_env`
  - 表示 governed ingress route 已存在，但 shared-token contract 尚未配置；生产 push 应 fail closed，不应 silent accept
- `auth_state = ready`
  - 表示 caller header + shared-token contract 已满足；live Signoz warning 可进入 admission path

### queue truth

- `pending`
  - warning 已 admitted，但尚未被 worker claim
- `processing`
  - warning 正在 worker 执行中
- `completed`
  - warning 已进入 canonical runtime spine 并留下 machine-readable processing result
- `failed`
  - 最近一次 worker attempt 失败，但仍可 retry
- `dead_letter`
  - warning 已超过 retry boundary，需要 operator 介入
- `deduped`
  - 当前 warning 与已有 active warning 命中同一 dedupe key，因此不再重复触发完整分析

### delivery / investigation summary

- `delivery_deferred_count`
  - 表示 runtime 已产出结果，但当前 delivery gate 仍未满足或被显式延后
- `cloud_fallback_ratio`
  - 表示已完成 warning 中，有多少比例进入了 `cloud_fallback` 调查层

## 4. Runtime / webhook evidence sidecar

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
- runtime summary 的 `rollout_evidence_path` 可直接作为 W7 audit 输入证据

## 5. Honest semantics

当前 baseline 的含义不是 “production rollout completed”，而是：

1. outcome admission surface 已 operator-visible
2. governed Signoz ingress truth 已 operator-visible
3. queue / backlog / dedupe / worker failure truth 已 operator-visible
4. delivery env gate truth 已 operator-visible
5. provider runtime gate truth 已 operator-visible
6. runtime/webhook path 可写出 closeout-ready machine evidence

它不表示：

- multi-env deployment ready
- secret-manager rollout ready
- external queue / bus scaling complete
- remote vendor production cutover complete

## 6. Minimum rollout checklist for operator truth

当前最小 checklist 固定为：

1. `/webhook/signoz` route 存在
2. `auth_state = ready`
3. accepted warning 会留下 durable admission truth
4. queue backlog 不为 silent unknown
5. `dead_letter` 可被 operator 看见
6. delivery deferred / provider fallback 不为 silent unknown
7. runtime sidecar 持续写出 `integration-rollout-evidence.v1`

若任一项不成立，不得 claim live-ready。

## 7. Governing files

- `app/integration_evidence.py`
- `app/receiver/alertmanager_webhook.py`
- `app/receiver/signoz_ingress.py`
- `app/receiver/signoz_queue.py`
- `app/receiver/signoz_worker.py`
- `app/storage/signoz_warning_store.py`
- `app/runtime_entry.py`
- `app/delivery/runtime.py`
- `app/delivery/env_gate.py`
- `app/investigator/provider_boundary.py`
- `tests/test_integration_evidence.py`
- `tests/test_signoz_warning_readiness.py`
