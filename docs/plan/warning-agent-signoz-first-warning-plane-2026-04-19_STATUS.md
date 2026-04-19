# warning-agent signoz-first warning plane status

- plan_id: `warning-agent-signoz-first-warning-plane-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- current_wave: `none`
- current_step: `closeout completed`
- last_updated: `2026-04-19`

## 1. Current truth

- predecessor pack `warning-agent-live-data-mvp-materialization-2026-04-19` is terminal/completed.
- user has explicitly frozen Prometheus-related task expansion and requested a Signoz-first rewrite plan.
- `S1` is completed:
  - packet contract now supports `candidate_source = signoz_alert`
  - `app/receiver/signoz_alert.py` landed with Signoz alert normalization and alert-ref extraction
  - runbook source-priority truth now lives in `docs/warning-agent-signoz-first-runbook.md`
  - predecessor MVP runbook is explicitly marked historical for source-priority decisions
- `S2` is completed:
  - `build_signoz_first_evidence_bundle(...)` landed
  - `build_prometheus_corroboration(...)` landed with Prometheus tolerated as optional all-`None` corroboration
  - `SignozCollector` now exposes `get_trace_details(...)` and `search_logs_by_trace_id(...)`
  - packet schemas now allow optional Signoz `alert_context` and `trace_detail_hints`
- `S3` is completed:
  - analyzer feature extraction now treats Signoz alert context and top-operation evidence as primary severity inputs
  - fast scorer reason codes now expose Signoz-primary routing signals
  - trained scorer now preserves the Signoz-first fast-scorer severity floor instead of downscoring Signoz-primary packets below baseline
- `S4` is now completed:
  - investigator tools now expose Signoz trace-detail and logs-by-trace wrappers
  - local-primary now has a Signoz-first investigation branch for `signoz_alert` packets
  - report rendering now emits Signoz-first narrative while preserving legacy manual-replay golden output
  - raw SigNoz trace-detail payloads are now normalized into packet trace-detail hints
- current repo truth:
  - live runtime can already build packet / decision / report from live evidence
  - Signoz-first bundle materialization can now produce a packet-compatible bundle without Prometheus
  - runtime scoring for a real `prod-hq-bff-service` Signoz-first bundle now yields `severity_band=P3`, `needs_investigation=True`, and Signoz-primary reason codes without Prometheus
  - real local-primary Signoz-first investigation now succeeds and emits Signoz-primary notes / refs / trace ids
  - current Prometheus is useful mainly as infra corroboration, not as the richest business warning truth
- new active workstream: `warning-agent-signoz-first-warning-plane-2026-04-19`

## 2. Why this plan now

The remaining honest gap is no longer “connect live data to the pipeline” — that is already done.
The remaining honest gap is:

- source priority is still mixed / ambiguous
- warning-agent does not yet fully use SigNoz alert and trace information
- Prometheus still has too much conceptual weight relative to its current real-world signal value

## 3. Current step

### `closeout`

Final objective achieved:

- Signoz-alert runtime entry now exists
- real Signoz-first runtime smoke has been executed
- control-plane and runbook truth have been updated with honest residuals

## 4. Recently completed

### `S5` — runtime / webhook / smoke / closeout

landed truth:

- updated `app/runtime_entry.py`
- updated `app/main.py`
- added `app/live_signoz_smoke.py`
- added `scripts/run_live_signoz_alert_smoke.py`
- added `fixtures/replay/signoz-alert.prod-hq-bff-service.error.json`
- added `tests/test_live_signoz_runtime.py`
- updated `tests/test_bootstrap.py`
- updated `docs/warning-agent-signoz-first-runbook.md`
- added `docs/plan/warning-agent-signoz-first-warning-plane-2026-04-19_CLOSEOUT.md`

review verdict:
- `accept_with_residuals`

landed truth summary:
- warning-agent now supports a Signoz-alert runtime entry surface
- direct real smoke `uv run python scripts/run_live_signoz_alert_smoke.py` produced packet / decision / investigation / report with `candidate_source=signoz_alert`
- report output remains Signoz-first even when the real runtime escalates to `cloud_fallback`
- residual: current real smoke still escalates to `cloud_fallback` under existing low-confidence policy, and live logs-by-trace remains best-effort

## 5. Next step

Hand off to:

- `none`

Next execution slice:

- `none`

## 6. Blockers / risks

1. current live Signoz smoke can still escalate to `cloud_fallback` under the existing low-confidence policy even though the primary evidence path is Signoz-first.
2. current SigNoz logs-by-trace surface remains best-effort and may fail open in the observed environment.
3. these residuals are runtime-quality residuals, not source-priority residuals.

## 7. Gate state

| gate | state | evidence |
|---|---|---|
| predecessor pack closed | pass | `warning-agent-live-data-mvp-materialization-2026-04-19` terminal completed |
| Prometheus freeze policy declared | pass | Signoz-first runbook freezes Prometheus expansion |
| S1 | pass | Signoz alert contract + packet candidate source landed |
| S2 | pass-with-residual | Signoz-first bundle path landed; real probe window variance remains possible |
| S3 | pass | real Signoz-first decision probe reaches `P3` + `needs_investigation=True` without Prometheus |
| S4 | pass-with-residual | real investigation/report path works; logs-by-trace remains best-effort |
| S5 | pass-with-residual | real Signoz-alert runtime smoke succeeded; runtime can still escalate to `cloud_fallback` |
| pack closeout | completed | closeout doc + runbook truth updated honestly |

## 8. Latest evidence

- production SigNoz active alert exists: `signoz error` / `ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0`
- production SigNoz provides real service-level top operations and error traces (e.g. `prod-hq-bff-service`, `g-crm-orch`, `prod-n-rms-pay-service`)
- direct trace detail evidence shows current SigNoz can expose:
  - response status code
  - downstream target / server address
  - parent-child span hierarchy
  - host identity
- targeted S5 verification passed:
  - `uv run pytest tests/test_live_runtime_entry.py tests/test_live_signoz_runtime.py tests/test_bootstrap.py` → `13 passed`
- direct live Signoz-alert smoke passed:
  - `uv run python scripts/run_live_signoz_alert_smoke.py`
  - produced `candidate_source=signoz_alert`
  - produced packet / decision / investigation / report
  - report contains `SigNoz primary evidence` and `Prometheus corroboration only`
- `uv run pytest` → `113 passed`
- `uv run ruff check app tests scripts` → pass
