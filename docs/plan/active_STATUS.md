# warning-agent local autopilot active status

- source_pack: `warning-agent-signoz-warning-production-2026-04-20`
- state: `completed`
- mirror_last_updated: `2026-04-20`

## Current Step

- active_step: `W7.RV1`
- active_wave: `closeout / W7 complete`
- intended_handoff: `plan-creator`

## Planned Stages

- [x] `W7.S1a` governed Signoz ingress route + caller contract freeze
- [x] `W7.S1b` durable warning admission ledger + provenance truth
- [x] `W7.S2a` dedupe key + queue ledger contract
- [x] `W7.S2b` worker lease / retry / dead-letter boundary
- [x] `W7.S3a` admitted warning -> packet / analyzer / report handoff
- [x] `W7.S3b` partial-evidence / delivery-deferred failure contract
- [x] `W7.S4a` operator readiness + rollout checklist truth
- [x] `W7.RV1` reality audit + W8 replan input

## Immediate Focus

### `W7.RV1`

- Owner: `execution-reality-audit`
- State: `COMPLETED`
- Priority: `highest`

结果：

- W7 closeout verdict = `accept_with_residuals`
- W8 replan input written
- next handoff = `plan-creator`

## Machine State

- active_step: `W7.RV1`
- latest_completed_step: `W7.RV1`
- intended_handoff: `plan-creator`
- latest_closeout_summary: W7 closed with a governed Signoz warning plane, durable admission + queue/worker truth, operator-visible readiness, and successor residuals routed to W8 hardening planning
- latest_verification:
  - `uv run pytest tests/test_signoz_alert_receiver.py tests/test_signoz_ingress_api.py tests/test_signoz_admission_storage.py tests/test_signoz_queue_contract.py tests/test_signoz_worker_runtime.py tests/test_signoz_warning_readiness.py tests/test_alertmanager_webhook.py tests/test_integration_evidence.py tests/test_live_signoz_runtime.py -> 29 passed`
  - `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 12 passed`
  - `uv run pytest -> 174 passed`
  - `uv run ruff check app tests scripts -> pass`

## Latest Evidence

- terminal W7 control-plane truth now points to `W7.RV1` with next handoff `plan-creator`
- closeout doc written at `docs/plan/warning-agent-signoz-warning-production-2026-04-20_CLOSEOUT.md`
- successor replan input written at `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`
