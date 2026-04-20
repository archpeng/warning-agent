# warning-agent provider boundary

## Current truth

`warning-agent` 的 investigator plane 现在有两层同时成立的 truth：

1. **current runtime smoke truth**
   - 默认仍运行 deterministic smoke provider
   - real adapter 仍然是 env-opt-in seam
   - 没有 runtime/live evidence 前，不得把 target model contract 误写成“已 live cutover”
2. **frozen operating contract truth**
   - `local_primary` 已冻结为 `Gemma4 26B` resident local investigator 的目标角色
   - `cloud_fallback` 已冻结为 `Neko API / OpenAI GPT-5.4 xhigh` sparse fallback 的目标角色
   - `local_primary` 的 `not_ready / degraded` 语义已冻结为 `fallback_or_queue`

当前 SSOT：

- `configs/escalation.yaml`
- `configs/provider-boundary.yaml`
- `app/investigator/provider_boundary.py`
- `app/investigator/local_primary.py`
- `app/runtime_entry.py`
- `app/receiver/alertmanager_webhook.py`
- `app/live_local_primary_smoke.py`
- `app/integration_evidence.py`

## Current smoke identity vs frozen operating contract

| provider | current smoke identity | frozen target identity | role | service mode | invocation scope |
|---|---|---|---|---|---|
| `local_primary` | `local_vllm / local-primary-smoke` | `gemma4 / gemma4-26b` | `primary_local_investigator` | `resident_prewarm_on_boot` | `needs_investigation_only` |
| `cloud_fallback` | `openai / cloud-fallback-smoke` | `neko_api_openai / gpt-5.4-xhigh` | `sparse_cloud_fallback` | `env_gated_remote` | `fallback_only` |

这表示：

1. 当前默认结果里若看到 smoke model identity，仍然是 honest current-runtime truth。
2. 但 operator / later execution slices 已经可以 machine-read：下一阶段要收成的真正目标模型分工是什么。
3. `PS.S1a` 冻结的是 **role contract**，不是 live rollout completed claim。

## Local-primary contract

`local_primary` 当前冻结为：

- role: `primary_local_investigator`
- target model: `gemma4 / gemma4-26b`
- service mode: `resident_prewarm_on_boot`
- invocation scope: `needs_investigation_only`
- readiness source: `resident_service`
- ready action: `invoke_when_needed`
- not-ready action: `fallback_or_queue`
- degraded action: `fallback_or_queue`
- fallback provider: `cloud_fallback`
- queue policy: `wait_for_local_primary_recovery`

语义是：

- 正常路径不应每次 warning 冷启动本地 26B
- warning-agent 只在 `3.6 Investigation` 需要时调用它
- 如果 resident local service 不 ready 或 degraded，行为必须是显式 `fallback_or_queue`，而不是 silent block

## Cloud-fallback contract

`cloud_fallback` 当前冻结为：

- role: `sparse_cloud_fallback`
- target model: `neko_api_openai / gpt-5.4-xhigh`
- service mode: `env_gated_remote`
- invocation scope: `fallback_only`
- readiness source: `env_gate`
- ready action: `invoke_when_selected`
- not-ready action: `fail_closed`
- degraded action: `fail_closed`

语义是：

- cloud fallback 不是 default first-hop investigator
- 它只处理 bounded fallback path
- 如果它自己不 ready，也不能 pretend live；必须 fail closed

## Resident local runtime truth

`PS.S2a` 之后，`local_primary` 不再只是“未来 resident”的 prose contract，而是有了实际 runtime lifecycle seam：

- FastAPI service boot 会执行一次 resident prewarm
- CLI/runtime entry boot 也会执行一次 resident prewarm
- `LocalPrimaryInvestigator.from_config(...)` 会复用同一 boot lifecycle，而不是每次 investigation 都重新 materialize provider

当前 lifecycle truth 固定为三种 machine states：

- `ready`
- `not_ready`
- `degraded`

当前 provider modes：

- `smoke_resident`
- `real_adapter_resident`

其中：

- `smoke_default` gate -> `smoke_resident + ready`
- `ready` gate -> `real_adapter_resident + ready`
- `missing_env` gate -> `real_adapter_resident + not_ready`
- resident prewarm materialization 失败 -> `real_adapter_resident + degraded`

当前 boot surfaces：

- `app/receiver/alertmanager_webhook.py` startup prewarm
- `app/runtime_entry.py` runtime-entry boot prewarm
- `app/live_local_primary_smoke.py` env-opt smoke boot prewarm

这表示：

1. 正常路径的 local-primary investigation 不再需要把 provider materialization 当成每次 warning 的冷启动步骤。
2. `3.6 Investigation` 仍然只在 `needs_investigation=true` 时真正调用 local-primary；boot prewarm 不等于 investigation inference。
3. local resident startup cost 现在和 `PS.S1b` 的 budget contract 一起固定为：**不计入 per-warning investigation budget**。

## Abnormal-path runtime policy

`PS.S2b` 之后，`local_primary` 的 `fallback_or_queue` 不再只是 config prose，而是有了明确 runtime policy：

- `direct_runtime`
  - `not_ready` -> `fallback_to_cloud_fallback`
  - `degraded` -> `fallback_to_cloud_fallback`
- `warning_worker`
  - `not_ready` -> `fallback_to_cloud_fallback`
  - `degraded` -> `queue_wait_for_local_primary_recovery`

当前语义是：

1. direct runtime / replay / webhook execution 没有 durable wait substrate，所以 resident local abnormal path 会直接走 bounded cloud fallback。
2. durable warning worker 在 local resident **曾 ready 但当前 degraded** 时，会把 warning 重新放回 `waiting_local_primary_recovery`，而不是 silent fail 或 generic retry。
3. `missing_env` / `not_ready` 仍走 explicit fallback，而不是假装“等一会可能会好”。

当前 queue-visible abnormal path truth：

- queue state 新增 `waiting_local_primary_recovery`
- queue entry 会留下：
  - `deferred_reason.code = local_primary_recovery_wait`
  - `policy_state.resident_lifecycle`
  - `policy_state.abnormal_path`

## Frozen real adapter contracts

以下 contract 已冻结，并已接到 runtime gate；但 **仍是 env-opt-in seam，不是 production rollout claim**。

| provider | frozen real adapter | transport | activation seam | required env seam | timeout |
|---|---|---|---|---|---|
| `local_primary` | `local_vllm_openai_compat` | `openai_compatible_http` | `env_opt_in` via `WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED` | `WARNING_AGENT_LOCAL_PRIMARY_BASE_URL`, `WARNING_AGENT_LOCAL_PRIMARY_MODEL`, optional `WARNING_AGENT_LOCAL_PRIMARY_API_KEY` | `45s` |
| `cloud_fallback` | `openai_responses_api` | `openai_responses_api` | `env_opt_in` via `WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED` | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `WARNING_AGENT_CLOUD_FALLBACK_MODEL` | `90s` |

runtime gate semantics：

1. gate off -> `smoke_default`
2. gate on but env missing -> `missing_env`
3. gate ready + runtime materialized -> direct runtime can use the frozen real adapter contract
4. gate ready + request/transport fails -> explicit fail closed or local fallback, never pretend-live success

`PS.S2c` 之后，`cloud_fallback` 现在不再只支持 injected fake client proof；它已经具备：

- auto-built `openai_responses_api` client when env gate is ready
- bounded handoff -> `/responses` request mapping
- mapped result notes proving real adapter transport path
- target identity frozen as:
  - target model provider: `neko_api_openai`
  - target model name: `gpt-5.4-xhigh`

由于 canonical `investigation-result.v1` 的 `model_provider` 仍保持旧 enum boundary，runtime result 里的 `model_provider` 继续诚实使用 contract-safe value；**Neko target identity 则通过 operator-visible contract + analysis notes 暴露**，而不是偷偷改 canonical contract。

## Why this boundary exists

当前 repo 要同时避免两种错误：

1. 把 smoke provider 误写成“目标模型已经 live”
2. 把未来目标模型角色只留在会话说明里，导致后续 slice 无法 deterministic 接手

因此边界固定为：

- smoke truth 继续诚实暴露 current runtime reality
- operating contract 真正冻结 Gemma4/Neko 的目标角色与 local not-ready semantics
- readiness / fallback / queue-wait 先写成 machine-readable contract，再进 runtime lifecycle slices

## Observable proof surfaces

- `tests/test_provider_boundary.py`
- `tests/test_local_primary.py`
- `tests/test_investigation_runtime.py`
- `tests/test_live_runtime_entry.py`
- `tests/test_live_investigation.py`
- `tests/test_integration_evidence.py`
- `tests/test_signoz_warning_readiness.py`

这些 proof 现在覆盖：

- smoke identity 与 target operating contract 可同时加载
- `local_primary` / `cloud_fallback` 的 target identities 与 role split 已冻结
- `local_primary` 的 `fallback_or_queue` 语义已 machine-readable
- provider gate 的 `smoke_default / missing_env / ready` 仍可直接证明
- operator readiness surface 会暴露 provider runtime contract，而不是只暴露 gate state
- local resident lifecycle seam 现在支持 boot-prewarm-once and reuse semantics
- runtime boot and service boot 都能证明 no-cold-start normal path 是显式 lifecycle truth，而不是只在文档里声明
- local abnormal path 现在 machine-materializes as direct fallback or warning-worker recovery-wait rather than generic silent degradation
- cloud fallback real adapter 现在支持 auto-built OpenAI Responses client and bounded Neko target identity mapping
