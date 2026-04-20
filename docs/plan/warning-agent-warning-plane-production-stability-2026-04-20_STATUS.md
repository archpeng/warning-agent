# warning-agent warning-plane production stability status

- plan_id: `warning-agent-warning-plane-production-stability-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- current_wave: `closeout / PS complete`
- current_step: `closeout complete`
- last_updated: `2026-04-20`

## 1. Current truth

- `P3-P5` local analyzer / investigator / cloud-fallback baseline 已 closed。
- `W7 signoz warning production` 已 landed governed ingress、durable admission、queue/worker boundary、readiness truth。
- `MM` bounded local-primary real adapter seam 已 landed 到 runtime auto-wiring。
- `PS` production-stability pack 现已完整执行并 closeout，closeout verdict：`accept_with_residuals`。
- closeout doc：`docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_CLOSEOUT.md`
- successor replan input：`docs/plan/warning-agent-warning-plane-production-stability-successor-replan-input-2026-04-20.md`

当前 repo 已真实具备：

- `local_primary` resident lifecycle seam：boot prewarm once + resident reuse + `ready / not_ready / degraded`
- explicit abnormal-path runtime policy：
  - direct runtime -> fallback to cloud
  - warning worker degraded -> `waiting_local_primary_recovery`
- bounded cloud fallback real-adapter path over OpenAI Responses API
- benchmark-backed `3.5 -> 3.6` stability gates
- operator-visible queue / delivery / feedback governance truth
- production-stability runbook + rollout evidence artifacts

## 2. Recently completed

### `PS.S2b` — local not-ready -> fallback or queue semantics

landed truth：

- `app/runtime_entry.py` now preserves explicit abnormal-path routing context
- `app/receiver/signoz_worker.py` now requeues resident degraded warnings as `waiting_local_primary_recovery`
- `app/storage/signoz_warning_store.py` now exposes recovery-wait queue state and metrics
- `app/integration_evidence.py` now exposes:
  - `provider_runtime.local_primary.resident_lifecycle`
  - `provider_runtime.local_primary.abnormal_path_policy`
- targeted proof passed:
  - `uv run pytest tests/test_investigation_runtime.py tests/test_signoz_queue_contract.py tests/test_signoz_worker_runtime.py tests/test_integration_evidence.py tests/test_signoz_warning_readiness.py tests/test_alertmanager_webhook.py`
  - result: `26 passed`

### `PS.S2c` — cloud fallback conversion to Neko GPT-5.4 xhigh

landed truth：

- new `app/investigator/cloud_fallback_openai_responses.py`
- `CloudFallbackInvestigator.from_config(...)` now auto-builds the real adapter client when gate is ready
- bounded cloud fallback handoff now materializes into `/responses` request mapping
- cloud result notes now expose target identity truth while canonical contract remains unchanged
- targeted proof passed:
  - `uv run pytest tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_integration_evidence.py tests/test_provider_boundary.py tests/test_signoz_warning_readiness.py`
  - result: `20 passed`

### `PS.S2d` — 3.5 -> 3.6 stability gates under the new split

landed truth：

- local analyzer benchmark accepted
- local-primary benchmark accepted and now includes:
  - `direct_runtime_abnormal_fallback_validity_rate`
  - `warning_worker_recovery_wait_validity_rate`
- cloud fallback benchmark accepted
- benchmark artifacts written to:
  - `data/benchmarks/local-analyzer-baseline-summary.json`
  - `data/benchmarks/local-primary-baseline-summary.json`
  - `data/benchmarks/cloud-fallback-baseline-summary.json`

### `PS.S3a` — warning-plane governance update for the new model topology

landed truth：

- `signoz_warning_plane.governance` now exposes queue state actions
- `delivery_bridge.governance` now exposes route mode / deferred behavior truth
- `feedback_loop` now exposes cadence / promotion / rollback governance in readiness/evidence baseline
- targeted proof passed:
  - `uv run pytest tests/test_signoz_queue_contract.py tests/test_delivery.py tests/test_feedback_governance.py tests/test_integration_evidence.py tests/test_signoz_warning_readiness.py tests/test_alertmanager_webhook.py`
  - result: `18 passed`

### `PS.S3b` — end-to-end production evidence pack + operator runbook

landed truth：

- updated docs:
  - `docs/warning-agent-provider-boundary.md`
  - `docs/warning-agent-integration-rollout-evidence.md`
- new runbook:
  - `docs/warning-agent-warning-plane-production-stability-runbook.md`
- runtime artifact proof written:
  - `data/rollout_evidence/ipk_checkout_post_api_pay_20260418t120008z.integration-rollout-evidence.json`
- benchmark scripts executed:
  - `uv run python scripts/run_local_analyzer_benchmark.py`
  - `uv run python scripts/run_local_primary_benchmark.py`
  - `uv run python scripts/run_cloud_fallback_benchmark.py`
- bounded local smoke executed:
  - `run_live_local_primary_adapter_smoke(...)`

### `PS.RV1` — reality audit + residual freeze

landed truth：

- closeout verdict: `accept_with_residuals`
- successor residual routing frozen into dedicated replan input
- next handoff: `plan-creator`

## 3. Next step

- current pack is terminally complete
- if work should continue, it must enter successor planning rather than reopen this pack

## 4. Residuals / risks

1. current pack does not claim all external live rollout work is finished.
2. if future work needs distributed queue / serving orchestration / multi-env rollout infra, that is a new boundary.
3. repo can now honestly claim production-operable stable output inside the current architecture boundary, but not universal live production rollout completion.

## 5. Gate state

| gate | state | evidence |
|---|---|---|
| `PS.S1a` | `completed` | model-role split + provider operating contract proof landed |
| `PS.S1b` | `completed` | local-primary high-budget contract landed |
| `PS.S2a` | `completed` | resident lifecycle seam landed |
| `PS.S2b` | `completed` | direct fallback / worker recovery-wait abnormal-path policy landed |
| `PS.S2c` | `completed` | bounded cloud real-adapter conversion landed |
| `PS.S2d` | `completed` | benchmark-backed stability gates landed |
| `PS.S3a` | `completed` | queue / delivery / feedback governance truth landed |
| `PS.S3b` | `completed` | operator runbook + evidence pack landed |
| `PS.RV1` | `completed` | closeout + residual freeze landed |

## 6. Latest evidence

- `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 12 passed`
- `uv run pytest -> 189 passed`
- `uv run ruff check app tests scripts -> pass`
- benchmark scripts produced accepted artifacts for analyzer / local-primary / cloud-fallback
- runtime entrypoint persisted rollout evidence artifact under `data/rollout_evidence/`
