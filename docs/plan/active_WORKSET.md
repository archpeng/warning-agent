# warning-agent local autopilot active workset

- source_pack: `warning-agent-signoz-warning-production-2026-04-20`
- queue_mode: `strict-serial`
- mirror_last_updated: `2026-04-20`

## Stage Order

- [x] `W7.S1a` governed Signoz ingress route + caller contract freeze
- [x] `W7.S1b` durable warning admission ledger + provenance truth
- [x] `W7.S2a` dedupe key + queue ledger contract
- [x] `W7.S2b` worker lease / retry / dead-letter boundary
- [x] `W7.S3a` admitted warning -> packet / analyzer / report handoff
- [x] `W7.S3b` partial-evidence / delivery-deferred failure contract
- [x] `W7.S4a` operator readiness + rollout checklist truth
- [x] `W7.RV1` reality audit + W8 replan input

## Active Stage

### `W7.RV1`

- Owner: `execution-reality-audit`
- State: `COMPLETED`
- Priority: `highest`

结果：

1. W7 reality audit closed with `accept_with_residuals`
2. successor residuals were frozen into W8 replan input
3. next handoff is `plan-creator`

## Machine Queue

- active_step: `W7.RV1`
- latest_completed_step: `W7.RV1`
- intended_handoff: `plan-creator`
- latest_closeout_summary: W7 completed with governed Signoz ingress, durable queue/worker truth, operator-visible readiness, and successor residuals routed to W8 hardening planning
- latest_verification:
  - `uv run pytest tests/test_signoz_alert_receiver.py tests/test_signoz_ingress_api.py tests/test_signoz_admission_storage.py tests/test_signoz_queue_contract.py tests/test_signoz_worker_runtime.py tests/test_signoz_warning_readiness.py tests/test_alertmanager_webhook.py tests/test_integration_evidence.py tests/test_live_signoz_runtime.py -> 29 passed`
  - `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 12 passed`
  - `uv run pytest -> 174 passed`
  - `uv run ruff check app tests scripts -> pass`
