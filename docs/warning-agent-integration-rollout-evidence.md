# warning-agent integration rollout evidence baseline

- status: `active-ssot`
- scope:
  - `W6.S4a` operator-visible rollout evidence
  - `W7.S4a` governed Signoz warning-plane readiness truth
  - `PS.S1a` provider role split + resident runtime contract freeze
  - `PS.S1b` high-budget local-primary contract alignment
  - webhook readiness evidence
  - runtime machine-readable rollout evidence sidecar
- last_updated: `2026-04-20`

## 1. Current truth

`warning-agent` 现在对 external integration / runtime rollout truth 提供两个直接可读的 evidence surface：

1. operator readiness surface：`GET /readyz`
2. runtime/webhook evidence sidecar：`integration-rollout-evidence.v1`

这两个 surface 现在共同覆盖：

- outcome admission
- governed Signoz warning ingress
- warning queue / backlog / dedupe / failure truth
- delivery env gate
- provider runtime gate
- provider operating contract

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
  - `pending / processing / waiting_local_primary_recovery / completed / failed / dead_letter / deduped`
  - `backlog_size`
  - `oldest_pending_age_sec`
  - `oldest_local_primary_recovery_wait_age_sec`
  - `processing_failure_count`
  - `local_primary_recovery_wait_count`
  - `delivery_deferred_count`
  - `cloud_fallback_ratio`
  - queue governance snapshot
- `adapter-feishu` 当前是 `ready` 还是 `missing_env`
- `local_primary` / `cloud_fallback` provider runtime truth：
  - current smoke identity
  - frozen operating contract
  - real-adapter gate state: `smoke_default / missing_env / ready`

## 3. Provider runtime reading guide

每个 `provider_runtime.<provider>` 现在至少包含：

- `mode`
- `smoke_model_provider`
- `smoke_model_name`
- `operating_contract`
- `budget_contract`（当前至少 `local_primary` 暴露）
- `resident_lifecycle`（当前至少 `local_primary` 暴露）
- `abnormal_path_policy`（当前至少 `local_primary` 暴露）
- `real_adapter`
- `transport`
- `enabled_env`
- `gate_state`
- `missing_env`
- `model_name`
- `endpoint`
- `fail_closed_action`

### `operating_contract`

`operating_contract` 是 `PS.S1a` 新增的 operator-visible truth，用来表达：

- 当前 provider 在目标架构里的角色
- target model identity
- service mode / invocation scope
- ready / not-ready / degraded 的 machine semantics

当前固定值：

#### `provider_runtime.local_primary.operating_contract`

- `provider_role = primary_local_investigator`
- `target_model_provider = gemma4`
- `target_model_name = gemma4-26b`
- `service_mode = resident_prewarm_on_boot`
- `invocation_scope = needs_investigation_only`
- `readiness_source = resident_service`
- `ready_action = invoke_when_needed`
- `not_ready_action = fallback_or_queue`
- `degraded_action = fallback_or_queue`
- `fallback_provider = cloud_fallback`
- `queue_policy = wait_for_local_primary_recovery`

#### `provider_runtime.cloud_fallback.operating_contract`

- `provider_role = sparse_cloud_fallback`
- `target_model_provider = neko_api_openai`
- `target_model_name = gpt-5.4-xhigh`
- `service_mode = env_gated_remote`
- `invocation_scope = fallback_only`
- `readiness_source = env_gate`
- `ready_action = invoke_when_selected`
- `not_ready_action = fail_closed`
- `degraded_action = fail_closed`

### `resident_lifecycle` + `abnormal_path_policy`

`PS.S2a` + `PS.S2b` 之后，operator 现在还能直接看到：

#### `provider_runtime.local_primary.resident_lifecycle`

- current resident state: `ready / not_ready / degraded`
- provider mode: `smoke_resident / real_adapter_resident`
- prewarm truth:
  - `prewarm_completed_once`
  - `prewarm_attempt_count`
  - `prewarm_source`
- boot startup cost policy

#### `provider_runtime.local_primary.abnormal_path_policy`

- `direct_runtime.not_ready = fallback_to_cloud_fallback`
- `direct_runtime.degraded = fallback_to_cloud_fallback`
- `warning_worker.not_ready = fallback_to_cloud_fallback`
- `warning_worker.degraded = queue_wait_for_local_primary_recovery`

这意味着 `/readyz` 已不只暴露 target contract，而是能直接告诉 operator：

- resident local 当前到底 ready 还是 degraded
- direct runtime 遇到 abnormal path 会怎么走
- durable warning worker 遇到 local recovery case 会怎么 requeue

### `budget_contract`

`PS.S1b` 进一步要求 operator-visible truth 不只看到“目标模型是谁”，还要看到：

- local-primary 的 investigation 预算已经不再是 smoke-era 小预算
- 这些预算是 **resident service ready 之后的 per-investigation caps**
- 它们**不包含 boot prewarm 成本**，因此不会把常驻预热语义误写成每次 warning 的冷启动成本

当前固定值：

#### `provider_runtime.local_primary.budget_contract`

- `profile = resident_26b_high_budget`
- `scope = per_investigation_when_resident_ready`
- `startup_cost_policy = excluded_from_per_warning_budget`
- `caps.wall_time_seconds = 300`
- `caps.max_tool_calls = 16`
- `caps.max_prompt_tokens = 12000`
- `caps.max_completion_tokens = 2400`
- `caps.max_retrieval_refs = 16`
- `caps.max_trace_refs = 8`
- `caps.max_log_refs = 8`
- `caps.max_code_refs = 8`

这意味着：

- `/readyz` 现在不会只告诉 operator “gate 现在开还是关”
- 还会告诉 operator：当前目标模型拓扑是什么、local not-ready 时系统如何退化、以及 local-primary 调查预算已经切换到 26B resident 语义

## 4. Signoz warning-plane reading guide

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
- `waiting_local_primary_recovery`
  - worker 已确认 resident local 处于 recovery-needed degraded state；warning 会在 recovery window 后重试，而不是 silent fail
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

### queue governance

`signoz_warning_plane.governance` 现在还会暴露：

- `queue_mode = strict_serial_warning_plane`
- `dedupe_scope = active_warning_eval_window`
- 每个 queue state 的 machine action

这让 operator 能直接分辨：

- `processing` 是 canonical runtime spine
- `waiting_local_primary_recovery` 是 local resident recovery wait
- `completed` 的 artifact 会继续喂给 delivery / feedback

### delivery + feedback governance

`delivery_bridge.governance` 现在会暴露：

- 每个 delivery class 的 route mode
- 哪些 route 是 `local_durable`
- 哪些 route 是 `env_gated_live`
- env gate 不满足时会显式 `deferred`

`feedback_loop` 现在会暴露：

- retrieval refresh cadence
- compare / retrain cadence
- promotion review policy
- rollback trigger rule
- runtime / previous artifact paths

## 5. Runtime / webhook evidence sidecar

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
- runtime summary 的 `rollout_evidence_path` 可直接作为 production-stability audit 输入证据

## 6. Honest semantics

当前 baseline 的含义不是 “production rollout completed”，而是：

1. outcome admission surface 已 operator-visible
2. governed Signoz ingress truth 已 operator-visible
3. queue / backlog / dedupe / worker failure truth 已 operator-visible
4. delivery env gate truth 已 operator-visible
5. provider runtime gate truth 已 operator-visible
6. provider target operating contract 已 operator-visible
7. local-primary resident lifecycle + abnormal path policy 已 operator-visible
8. delivery governance + feedback governance 已 operator-visible
9. local-primary high-budget contract 已 operator-visible
10. runtime/webhook path 可写出 closeout-ready machine evidence

它不表示：

- multi-env deployment ready
- secret-manager rollout ready
- resident Gemma4 lifecycle 已 materialized
- Neko GPT-5.4 xhigh live cutover 已完成
- external queue / bus scaling complete
- remote vendor production cutover complete

## 7. Minimum rollout checklist for operator truth

当前最小 checklist 固定为：

1. `/webhook/signoz` route 存在
2. `auth_state = ready`
3. accepted warning 会留下 durable admission truth
4. queue backlog 不为 silent unknown
5. `dead_letter` 可被 operator 看见
6. delivery deferred / provider fallback 不为 silent unknown
7. provider operating contract 对当前目标模型拓扑是显式的
8. local-primary resident lifecycle 与 abnormal-path policy 对 operator 是显式的
9. delivery governance 与 feedback governance 对 operator 是显式的
10. local-primary high-budget contract 对 operator 是显式的
11. runtime sidecar 持续写出 `integration-rollout-evidence.v1`

若任一项不成立，不得 claim live-ready。

## 8. Governing files

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
- `configs/provider-boundary.yaml`
- `configs/escalation.yaml`
- `tests/test_integration_evidence.py`
- `tests/test_signoz_warning_readiness.py`
