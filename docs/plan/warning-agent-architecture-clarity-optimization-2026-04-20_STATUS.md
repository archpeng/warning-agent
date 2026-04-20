# warning-agent architecture clarity optimization status

- plan_id: `warning-agent-architecture-clarity-optimization-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- current_wave: `closeout / AC complete`
- current_step: `closeout complete`
- last_updated: `2026-04-20`

## 1. Current truth

- predecessor pack `warning-agent-warning-plane-production-stability-2026-04-20` 已在 `PS.RV1` closeout，作为本 pack 的前置条件保持 closed。
- 当前 architecture-clarity pack 已完整执行并 closeout，verdict=`accept_with_residuals`。
- closeout doc：`docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_CLOSEOUT.md`
- successor replan input：`docs/plan/warning-agent-architecture-clarity-optimization-successor-replan-input-2026-04-20.md`

当前 repo 已真实具备：

- explicit architecture-clarity guardrails and target map
- `3.5` analyzer runtime/training/corpus split
- `3.5` minimal assist/audit internal records
- `3.6` local-primary resident-lifecycle seam extraction
- `3.6` cloud-fallback brief/request seam extraction
- normalized-alert shared receiver contracts to reduce packet/receiver coupling
- `3.6` minimal internal records for later learning optimization

## 2. Recently completed

### `AC.S1a` — architecture clarity guardrail freeze + hotspot map

landed truth：

- new docs:
  - `docs/warning-agent-architecture-clarity-guardrails.md`
  - updates to `docs/warning-agent-architecture.md`
  - updates to `docs/warning-agent-provider-boundary.md`
  - updates to `docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`
- explicit no-overengineering and protected-surface truth now exists
- hotspot inventory for `3.5` / `3.6` is now explicit and machine-readable through the pack docs

### `AC.S1b` — dependency hygiene target map + runtime/benchmark ownership inventory

landed truth：

- new doc:
  - `docs/warning-agent-architecture-clarity-target-map.md`
- runtime-vs-benchmark ownership and dependency hygiene move map now explicit
- package/export/direction concerns are now clustered into bounded follow-up slices instead of implicit code review comments

### `AC.S2a` — `3.5` runtime/training boundary cleanup

landed truth：

- new modules:
  - `app/analyzer/corpus_packets.py`
  - `app/analyzer/trained_scorer_runtime.py`
  - `app/analyzer/trained_scorer_training.py`
- `app/analyzer/trained_scorer.py` now acts as compatibility facade
- `app/analyzer/calibrate.py` now uses corpus packet helper instead of owning receiver/packet materialization glue directly

### `AC.S2b` — `3.5` assist/audit groundwork

landed truth：

- new module:
  - `app/analyzer/internal_records.py`
- new tests:
  - `tests/test_analyzer_internal_records.py`
- `SidecarAssistPacket` and `DecisionAuditRecord` now exist as non-canonical internal objects

### `AC.S3a` — `3.6` local-primary internal split

landed truth：

- new module:
  - `app/investigator/local_primary_resident.py`
- `app/investigator/local_primary.py` now delegates resident lifecycle / abnormal-path machine truth to the resident seam module while preserving investigator-facing entrypoints

### `AC.S3b` — `3.6` cloud-fallback internal split

landed truth：

- new module:
  - `app/investigator/cloud_fallback_brief.py`
- `app/investigator/cloud_fallback.py` now focuses more narrowly on provider execution / guards / result materialization
- `app/investigator/cloud_fallback_openai_responses.py` now consumes the brief module directly

### `AC.S3c` — execution spine and normalized-alert dependency hygiene

landed truth：

- new shared contract module:
  - `app/receiver/contracts.py`
- updated modules:
  - `app/packet/builder.py`
  - `app/receiver/alertmanager_webhook.py`
  - `app/receiver/signoz_alert.py`
  - `app/collectors/evidence_bundle.py`
- packet builder no longer depends on webhook implementation types directly

### `AC.S4a` — minimal internal learning objects + docs/benchmark alignment

landed truth：

- new module:
  - `app/investigator/internal_records.py`
- new tests:
  - `tests/test_investigator_internal_records.py`
  - `tests/test_module_boundaries.py`
- future note and provider boundary docs now point to the minimal groundwork code surfaces

### `AC.RV1` — reality audit + residual freeze

landed truth：

- closeout verdict: `accept_with_residuals`
- successor residual routing frozen into dedicated replan input
- next handoff: `plan-creator`

## 3. Next step

- current pack is terminally complete
- if work should continue, it must enter successor planning rather than reopen this pack

## 4. Residuals / risks

1. current pack does not claim `3.5/3.6` learning optimization is finished; it only claims the codebase is structurally clearer and minimally prepared.
2. `app/collectors/evidence_bundle.py` and `app/storage/signoz_warning_store.py` remain known hotspots and may need a later bounded pack.
3. any future `warning-core` extraction still requires a new explicit pack.

## 5. Gate state

| gate | state | evidence |
|---|---|---|
| `AC.S1a` | `completed` | guardrail doc + hotspot map landed |
| `AC.S1b` | `completed` | target map + ownership inventory landed |
| `AC.S2a` | `completed` | analyzer runtime/training split landed |
| `AC.S2b` | `completed` | analyzer assist/audit internal records landed |
| `AC.S3a` | `completed` | local-primary resident seam landed |
| `AC.S3b` | `completed` | cloud-fallback brief seam landed |
| `AC.S3c` | `completed` | normalized-alert shared contract seam landed |
| `AC.S4a` | `completed` | minimal investigator internal records landed |
| `AC.RV1` | `completed` | closeout + residual freeze landed |

## 6. Latest evidence

- `uv run pytest tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 18 passed`
- `uv run pytest tests/test_trained_scorer.py tests/test_benchmark.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 53 passed`
- `uv run pytest tests/test_module_boundaries.py tests/test_analyzer_internal_records.py tests/test_investigator_internal_records.py tests/test_provider_boundary.py tests/test_trained_scorer.py tests/test_benchmark.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_signoz_worker_runtime.py tests/test_signoz_queue_contract.py tests/test_signoz_warning_readiness.py tests/test_signoz_ingress_api.py tests/test_signoz_alert_receiver.py tests/test_live_runtime_entry.py tests/test_live_investigation.py tests/test_feedback_governance.py tests/test_delivery.py tests/test_investigator_benchmark.py tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py -> 96 passed`
- `uv run pytest -> 203 passed`
- `uv run ruff check app tests scripts -> pass`
