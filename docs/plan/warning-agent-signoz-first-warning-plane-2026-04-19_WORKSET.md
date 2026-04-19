# warning-agent signoz-first warning plane workset

- plan_id: `warning-agent-signoz-first-warning-plane-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- queue_mode: `strict-serial`
- active_wave: `none`
- active_slice: `none`
- last_updated: `2026-04-19`

## Global freeze rule

Prometheus-related task expansion is frozen for this pack.

Do not do any of the following inside this workstream:

- add new Prometheus primary metrics
- expand Prometheus query family coverage
- make Prometheus the primary severity source again
- make Prometheus the primary investigation source again

Permitted Prometheus work:

- compatibility / bugfix only
- optional infra corroboration only

## Recently completed

### `S1` — freeze Prometheus role + Signoz-first contracts

- state: `done`
- evidence:
  - updated `app/packet/contracts.py`
  - updated `schemas/incident-packet.v1.json`
  - updated `schemas/incident-packet.v2.json`
  - updated `app/receiver/alertmanager_webhook.py`
  - added `app/receiver/signoz_alert.py`
  - updated `app/receiver/__init__.py`
  - added `tests/test_signoz_alert_receiver.py`
  - updated `tests/test_packet_builder.py`
  - updated `docs/warning-agent-live-data-mvp-runbook.md`
  - added `docs/warning-agent-signoz-first-runbook.md`
  - `uv run pytest tests/test_packet_builder.py tests/test_signoz_alert_receiver.py` → `5 passed`
  - `uv run pytest` → `104 passed`
  - `uv run ruff check app tests scripts` → pass
- closeout note:
  - Signoz alert normalization contract now exists
  - packet candidate source now supports `signoz_alert`
  - Prometheus expansion freeze is encoded in runbook + plan truth

### `S2` — Signoz alert -> evidence bundle materialization

- state: `done`
- evidence:
  - updated `app/collectors/evidence_bundle.py`
  - updated `app/collectors/signoz.py`
  - updated `app/packet/contracts.py`
  - updated `app/receiver/alertmanager_webhook.py`
  - updated `app/receiver/signoz_alert.py`
  - updated `schemas/incident-packet.v1.json`
  - updated `schemas/incident-packet.v2.json`
  - updated `configs/evidence.yaml`
  - updated `tests/test_signoz_collector.py`
  - updated `tests/test_signoz_alert_receiver.py`
  - updated `tests/test_live_evidence_bundle.py`
  - added `tests/test_signoz_primary_bundle.py`
  - `uv run pytest tests/test_packet_builder.py tests/test_signoz_collector.py tests/test_signoz_alert_receiver.py tests/test_live_evidence_bundle.py tests/test_signoz_primary_bundle.py` → `17 passed`
  - direct Signoz-first bundle probe against `prod-hq-bff-service` succeeded with non-fallback top-operation evidence and alert-context refs while Prometheus remained all-`None`
  - `uv run pytest` → `107 passed`
  - `uv run ruff check app tests scripts` → pass
- closeout note:
  - Signoz-first bundle construction no longer depends on Prometheus
  - bounded alert refs and trace-detail hints can now be carried in Signoz evidence
  - residual: latest real probe window did not return live trace ids for `prod-hq-bff-service`

### `S3` — Signoz-first analyzer + routing

- state: `done`
- evidence:
  - updated `app/analyzer/base.py`
  - updated `app/analyzer/fast_scorer.py`
  - updated `app/analyzer/trained_scorer.py`
  - added `tests/test_signoz_first_routing.py`
  - `uv run pytest tests/test_fast_scorer.py tests/test_trained_scorer.py tests/test_live_runtime_entry.py tests/test_signoz_first_routing.py` → `10 passed`
  - direct Signoz-first decision probe against `prod-hq-bff-service` now yields `P3` + `needs_investigation=True` without Prometheus
  - `uv run pytest` → `109 passed`
  - `uv run ruff check app tests scripts` → pass
- closeout note:
  - Signoz alert context and top operations now drive non-`P4` severity without Prometheus
  - trained scorer preserves the Signoz-first fast-scorer floor

### `S4` — Signoz-first investigation + report

- state: `done`
- evidence:
  - updated `app/investigator/tools.py`
  - updated `app/investigator/local_primary.py`
  - updated `app/investigator/router.py`
  - updated `app/reports/markdown_builder.py`
  - updated `app/collectors/evidence_bundle.py`
  - updated `tests/test_investigator_tools.py`
  - updated `tests/test_live_investigation.py`
  - added `tests/test_signoz_first_report.py`
  - updated `tests/test_signoz_primary_bundle.py`
  - `uv run pytest tests/test_signoz_primary_bundle.py tests/test_investigator_tools.py tests/test_live_investigation.py tests/test_markdown_builder.py tests/test_signoz_first_report.py tests/test_signoz_first_routing.py` → `16 passed`
  - direct Signoz-first investigation probe against `prod-hq-bff-service` now succeeds with route gating, Signoz-first notes, and Signoz-first report strings
  - `uv run pytest` → `113 passed`
  - `uv run ruff check app tests scripts` → pass
- closeout note:
  - Signoz-first investigation/report path now works end-to-end at the packet/decision/investigation/report layer
  - residual: live logs-by-trace remains best-effort and may fail open without collapsing the investigation

### `S5` — runtime / webhook / smoke / closeout

- state: `done`
- evidence:
  - updated `app/runtime_entry.py`
  - updated `app/main.py`
  - added `app/live_signoz_smoke.py`
  - added `scripts/run_live_signoz_alert_smoke.py`
  - added `fixtures/replay/signoz-alert.prod-hq-bff-service.error.json`
  - added `tests/test_live_signoz_runtime.py`
  - updated `tests/test_bootstrap.py`
  - updated `docs/warning-agent-signoz-first-runbook.md`
  - added `docs/plan/warning-agent-signoz-first-warning-plane-2026-04-19_CLOSEOUT.md`
  - `uv run pytest tests/test_live_runtime_entry.py tests/test_live_signoz_runtime.py tests/test_bootstrap.py` → `13 passed`
  - `uv run python scripts/run_live_signoz_alert_smoke.py` produced a real Signoz-alert runtime summary with packet / decision / investigation / report
  - `uv run pytest` → `113 passed`
  - `uv run ruff check app tests scripts` → pass
- closeout note:
  - Signoz-alert runtime entry now exists end-to-end
  - residual: the current real smoke still escalates to `cloud_fallback` under existing low-confidence policy

## Active slice

- none; pack is closed out

## Queue

| Slice | State | Summary | Depends on |
|---|---|---|---|
| `S1` | `done` | freeze Prometheus role + Signoz-first contracts | predecessor closeout |
| `S2` | `done` | Signoz alert -> evidence bundle materialization | `S1` |
| `S3` | `done` | Signoz-first analyzer + routing | `S2` |
| `S4` | `done` | Signoz-first investigation + report | `S3` |
| `S5` | `done` | runtime / webhook / smoke / closeout | `S4` |

## Slice handoff notes

### `S2`
- do not add any new Prometheus expansion work
- if Signoz logs remain weak, treat traces/top ops/trace details as primary truth instead of forcing log-first design

### `S3`
- this is the first slice allowed to change severity / routing behavior
- if packet contract still cannot hold needed Signoz alert metadata, stop and replan rather than smuggling data through legacy Prometheus slots

### `S4`
- Prometheus may appear in report only as corroboration note
- Signoz refs / trace hierarchy / downstream service should be the main investigation evidence

### `S5`
- closeout requires at least one honest Signoz-first live runtime proof
- if current real case still does not enter investigation, final verdict must explain whether that is a routing policy issue or truly weak evidence
