# warning-agent architecture clarity optimization closeout

- plan_id: `warning-agent-architecture-clarity-optimization-2026-04-20`
- closeout_date: `2026-04-20`
- verdict: `accept_with_residuals`
- next_handoff: `plan-creator`

## 1. Scope audited

审计对象：`warning-agent architecture clarity optimization`

claimed outcomes：

- `3.5` runtime / training / benchmark / assist / audit boundaries are clearer than the predecessor closeout baseline
- `3.6` local-primary / cloud-fallback / execution-spine boundaries are clearer than the predecessor closeout baseline
- future-note groundwork now has minimal internal code objects instead of living only in prose
- the repo stayed inside its architecture boundary and did not drift into `warning-core`, generic state/policy frameworks, or platform work

## 2. Findings

### confirmed

1. architecture-clarity guardrails are now explicit and operator-readable:
   - `docs/warning-agent-architecture-clarity-guardrails.md`
   - `docs/warning-agent-architecture-clarity-target-map.md`
2. `3.5` analyzer runtime/training ownership is materially clearer:
   - `app/analyzer/trained_scorer_runtime.py`
   - `app/analyzer/trained_scorer_training.py`
   - `app/analyzer/trained_scorer.py` now acts as a compatibility facade
   - `app/analyzer/corpus_packets.py` now owns replay/evidence corpus packet materialization
   - `app/analyzer/calibrate.py` no longer directly owns packet/receiver materialization glue
3. `3.5` minimal internal groundwork landed without changing canonical output:
   - `app/analyzer/internal_records.py`
   - `tests/test_analyzer_internal_records.py`
   - `SidecarAssistPacket` and `DecisionAuditRecord` now exist as non-canonical internal records
4. `3.6` local-primary seams are materially clearer:
   - `app/investigator/local_primary_resident.py` now owns resident lifecycle + abnormal-path truth
   - `app/investigator/local_primary.py` remains the investigator-facing entrypoint and real-adapter seam
5. `3.6` cloud-fallback seams are materially clearer:
   - `app/investigator/cloud_fallback_brief.py` now owns bounded brief / request mapping
   - `app/investigator/cloud_fallback.py` remains the provider execution / guard / result materialization surface
   - `app/investigator/cloud_fallback_openai_responses.py` now consumes the brief module directly
6. execution-spine dependency hygiene improved:
   - `app/receiver/contracts.py` now owns normalized alert contracts
   - `app/packet/builder.py` no longer imports normalized alert types from webhook implementation code
   - `app/receiver/signoz_alert.py` and `app/collectors/evidence_bundle.py` now use the shared contract surface
7. minimal `3.6` future-learning groundwork landed:
   - `app/investigator/internal_records.py`
   - `tests/test_investigator_internal_records.py`
   - `ActionTrace`, `InvestigationEvidencePack`, and `CompressedInvestigationBrief` now exist as non-canonical internal records
8. proof surfaces were added for structure, not only behavior:
   - `tests/test_architecture_clarity_docs.py`
   - `tests/test_module_boundaries.py`
9. full validation passed:
   - `uv run pytest` → `203 passed`
   - `uv run ruff check app tests scripts` → pass

### drift avoided

1. no canonical contract was changed.
2. no provider topology was changed.
3. no `warning-core` extraction was mixed into the pack.
4. no generic `app/state/*` / `app/policies/*` framework was introduced.
5. no online learning / auto-promotion semantics were introduced.

### residuals kept honest

1. the repo is now structurally clearer, but `3.5/3.6` learning optimization itself is not yet complete.
2. `app/collectors/evidence_bundle.py` and `app/storage/signoz_warning_store.py` remain known hotspots and were intentionally not expanded into a broader redesign in this pack.
3. current minimal internal objects are groundwork only; they are not yet a full replay/compare/policy loop.

## 3. Evidence added / reused

### targeted proofs

- `uv run pytest tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py` → `18 passed`
- `uv run pytest tests/test_analyzer_internal_records.py tests/test_investigator_internal_records.py tests/test_module_boundaries.py` → included in later full targeted suites
- `uv run pytest tests/test_trained_scorer.py tests/test_benchmark.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py` → `53 passed`
- `uv run pytest tests/test_module_boundaries.py tests/test_analyzer_internal_records.py tests/test_investigator_internal_records.py tests/test_provider_boundary.py tests/test_trained_scorer.py tests/test_benchmark.py tests/test_local_primary.py tests/test_cloud_fallback.py tests/test_investigation_runtime.py tests/test_runtime_entry.py tests/test_alertmanager_webhook.py tests/test_signoz_worker_runtime.py tests/test_signoz_queue_contract.py tests/test_signoz_warning_readiness.py tests/test_signoz_ingress_api.py tests/test_signoz_alert_receiver.py tests/test_live_runtime_entry.py tests/test_live_investigation.py tests/test_feedback_governance.py tests/test_delivery.py tests/test_investigator_benchmark.py tests/test_architecture_clarity_docs.py tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py tests/test_bootstrap.py` → `96 passed`

### full gates

- `uv run pytest` → `203 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during this pack

- explicit architecture-clarity guardrail doc and target-map doc
- analyzer runtime/training split via runtime/training/corpus helper modules
- analyzer minimal internal assist/audit records
- local-primary resident-lifecycle seam extraction
- cloud-fallback brief/request seam extraction
- normalized-alert shared receiver contracts
- investigator minimal internal records for future learning groundwork
- structural proof tests for docs and module boundaries

## 5. Successor residuals / replan input

1. If future work wants to optimize `3.5` policy quality, it should now build on the landed assist/audit seams rather than reopen runtime shell or canonical decision contract.
2. If future work wants to optimize `3.6` evidence search / stop / compression policy, it should build on the landed local/cloud internal seams rather than reopen provider topology.
3. If future work wants `warning-core` extraction, it must be a later pack after internal objects and compare surfaces are more stable.

具体 successor input 见：

- `docs/plan/warning-agent-architecture-clarity-optimization-successor-replan-input-2026-04-20.md`

## 6. Closeout verdict

本 pack 可以以 `accept_with_residuals` closeout。

理由：

- `3.5` 与 `3.6` 的结构清晰度提升已经真实落地到代码、tests、docs，而不只是文档主张。
- 当前 pack 成功完成了 minimal groundwork，同时避免了 overengineering drift。
- remaining residuals 都属于后续更深 learning optimization / extraction gate work，而不是当前 clarity pack 未闭合。

## 7. Successor handoff

- 当前停止在 `AC.RV1` terminal truth。
- 若继续推进更深的 `3.5 / 3.6` learning optimization、compare surfaces、or extraction gate work，必须进入 successor planning；不得继续在当前 clarity pack 中混做。
