# warning-agent warning-plane production stability runbook

## Scope

This runbook is the operator-facing source of truth for the current warning-plane production-stability topology:

- `local_primary` = resident local-first `Gemma4 26B` investigation role
- `cloud_fallback` = bounded sparse fallback on `Neko API / OpenAI GPT-5.4 xhigh`
- local abnormal path = explicit `fallback_to_cloud_fallback` or `queue_wait_for_local_primary_recovery`

It does **not** claim that external production rollout is complete in every environment. It documents the current repo-local operating semantics, enable/disable levers, rollback levers, and triage checkpoints.

## 1. Current model topology

### normal path

- first-pass analyzer decides whether `3.6 Investigation` is needed
- if not needed, no investigator call happens
- if needed and resident local is `ready`, `local_primary` handles the investigation
- `cloud_fallback` is not first-hop by default

### abnormal path

- `direct_runtime.not_ready` -> `fallback_to_cloud_fallback`
- `direct_runtime.degraded` -> `fallback_to_cloud_fallback`
- `warning_worker.not_ready` -> `fallback_to_cloud_fallback`
- `warning_worker.degraded` -> `queue_wait_for_local_primary_recovery`

## 2. Enable / disable switches

### local_primary real adapter

Enable:

- `WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED=true`
- `WARNING_AGENT_LOCAL_PRIMARY_BASE_URL=<local openai-compatible endpoint>`
- `WARNING_AGENT_LOCAL_PRIMARY_MODEL=gemma4-26b`
- optional: `WARNING_AGENT_LOCAL_PRIMARY_API_KEY=<token>`

Disable / rollback to smoke:

- unset `WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED`
- or remove required endpoint/model env so gate is no longer `ready`

Expected `/readyz` surfaces:

- `provider_runtime.local_primary.gate_state`
- `provider_runtime.local_primary.resident_lifecycle`
- `provider_runtime.local_primary.abnormal_path_policy`

### cloud_fallback real adapter

Enable:

- `WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED=true`
- `OPENAI_BASE_URL=<neko openai-compatible responses endpoint>`
- `OPENAI_API_KEY=<token>`
- `WARNING_AGENT_CLOUD_FALLBACK_MODEL=gpt-5.4-xhigh`

Disable / rollback to smoke:

- unset `WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED`

Expected `/readyz` surfaces:

- `provider_runtime.cloud_fallback.gate_state`
- `provider_runtime.cloud_fallback.operating_contract.target_model_provider = neko_api_openai`
- `provider_runtime.cloud_fallback.operating_contract.target_model_name = gpt-5.4-xhigh`

## 3. Boot + readiness procedure

1. Start the service or runtime entrypoint.
2. Check `GET /readyz`.
3. Confirm:
   - `status = ready`
   - `provider_runtime.local_primary.resident_lifecycle.state = ready` for resident-ready local path
   - `provider_runtime.local_primary.abnormal_path_policy.warning_worker.degraded = queue_wait_for_local_primary_recovery`
   - `signoz_warning_plane.governance.queue_mode = strict_serial_warning_plane`
4. If cloud fallback should be live, also confirm:
   - `provider_runtime.cloud_fallback.gate_state = ready`
   - cloud target contract still points at `neko_api_openai / gpt-5.4-xhigh`

## 4. Queue triage procedure

Use `/readyz` + warning-store artifacts to classify queue health.

### healthy steady state

- `backlog_size` small or zero
- `local_primary_recovery_wait_count = 0`
- `processing_failure_count = 0`

### local resident recovery wait

Signals:

- `queue_states.waiting_local_primary_recovery > 0`
- `local_primary_recovery_wait_count > 0`
- warning queue entries contain:
  - `deferred_reason.code = local_primary_recovery_wait`
  - `policy_state.resident_lifecycle.state = degraded`
  - `policy_state.abnormal_path.action = queue_wait_for_local_primary_recovery`

Operator action:

1. verify local resident endpoint health
2. restore local endpoint readiness
3. let worker retry after `next_attempt_after`
4. if recovery is not imminent, disable local real adapter and allow fallback path instead

### cloud fallback pressure

Signals:

- `cloud_fallback_ratio` rises materially
- direct runtime / worker abnormal paths are falling back instead of staying local

Operator action:

1. verify local resident health first
2. confirm cloud env gate is intentionally enabled
3. inspect cloud fallback notes in investigation artifacts for bounded handoff correctness

### dead-letter / failure pressure

Signals:

- `processing_failure_count > 0`
- queue state enters `dead_letter`

Operator action:

1. inspect queue entry `last_error`
2. determine whether failure is local resident, cloud transport, delivery bridge, or runtime validation
3. rollback the failing plane if needed

## 5. Delivery governance

Current delivery policy:

- `observe` -> local durable markdown only
- `open_ticket` -> local durable ticket queue
- `page_owner` -> env-gated live `adapter_feishu`
- `send_to_human_review` -> local durable review queue

If env gate is not ready, `page_owner` becomes explicit `deferred`, not silent delivery loss.

Check:

- `delivery_bridge.env_gate_state`
- `delivery_bridge.governance`
- delivery dispatch artifacts under `data/.../deliveries`

## 6. Feedback governance

Current feedback policy stays governed and manual-review-oriented:

- retrieval refresh: `on_each_landed_outcome`
- compare / retrain: repo-local governed cadence
- promotion: not auto-promoted
- rollback: previous runtime artifact remains available

Check:

- `feedback_loop` in `/readyz`
- `configs/feedback-governance.yaml`
- outcome admission receipts from `/outcome/admit`

## 7. Benchmark / evidence checklist

Before claiming stable-output progress, collect:

- `uv run python scripts/run_local_analyzer_benchmark.py`
- `uv run python scripts/run_local_primary_benchmark.py`
- `uv run python scripts/run_cloud_fallback_benchmark.py`
- targeted runtime proofs for:
  - resident local ready path
  - direct fallback path
  - warning-worker recovery-wait path
  - cloud fallback real adapter mapping

Expected artifact family:

- `data/benchmarks/local-analyzer-baseline-summary.json`
- `data/benchmarks/local-primary-baseline-summary.json`
- `data/benchmarks/cloud-fallback-baseline-summary.json`
- runtime rollout evidence under `rollout_evidence/*.integration-rollout-evidence.json`

## 8. Honest rollback rule

Rollback immediately if either is true:

- resident local path is not ready and recovery wait is accumulating without recovery
- cloud real adapter path is timing out or failing validation and begins fail-closing repeatedly

Rollback target order:

1. disable cloud real adapter if cloud path is the failing plane
2. disable local real adapter if resident local path is the failing plane
3. return to smoke + fail-closed governed behavior rather than pretending live success
