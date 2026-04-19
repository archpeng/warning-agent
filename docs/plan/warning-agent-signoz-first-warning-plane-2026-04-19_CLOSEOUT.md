# warning-agent signoz-first warning plane closeout

- plan_id: `warning-agent-signoz-first-warning-plane-2026-04-19`
- status: `completed`
- closeout_verdict: `accept_with_residuals`
- predecessor_plan: `warning-agent-live-data-mvp-materialization-2026-04-19`
- completed_at: `2026-04-19`

## 1. Goal verdict

Goal achieved:

- **SigNoz alert** is now the primary warning input contract
- **SigNoz traces / top operations / trace details** are now the primary severity + investigation evidence path
- **Prometheus** is retained only as optional infra corroboration

This closes the successor pack at the intended source-priority boundary.

## 2. Landed slices

### `S1` — freeze Prometheus role + Signoz-first contracts
- landed `candidate_source = signoz_alert`
- landed Signoz alert normalization + alert refs
- landed Signoz-first runbook truth and Prometheus freeze

### `S2` — Signoz alert -> evidence bundle materialization
- landed `build_signoz_first_evidence_bundle(...)`
- landed `build_prometheus_corroboration(...)`
- landed Signoz alert context + trace-detail hints in packet-compatible Signoz evidence
- landed SigNoz collector wrappers for trace details + logs-by-trace

### `S3` — Signoz-first analyzer + routing
- landed Signoz-primary feature extraction in analyzer base
- landed Signoz-primary fast scorer reason codes
- landed trained scorer floor so Signoz-primary packets are not downscored below fast-scorer truth
- landed hybrid routing gate for Signoz-primary low-confidence investigations

### `S4` — Signoz-first investigation + report
- landed Signoz-first local-primary investigation branch
- landed Signoz trace-detail + logs-by-trace bounded tools
- landed Signoz-first report rendering while preserving legacy golden replay reports
- landed raw trace-detail payload normalization support for packet hint extraction

### `S5` — runtime / smoke / closeout
- landed `warning-agent signoz-alert <fixture>` runtime entry
- landed `app/live_signoz_smoke.py`
- landed `scripts/run_live_signoz_alert_smoke.py`
- landed Signoz alert fixture `fixtures/replay/signoz-alert.prod-hq-bff-service.error.json`
- landed closeout/runbook truth updates

## 3. Verification evidence

### targeted gates
- `uv run pytest tests/test_packet_builder.py tests/test_signoz_collector.py tests/test_signoz_alert_receiver.py tests/test_live_evidence_bundle.py tests/test_signoz_primary_bundle.py` → `17 passed`
- `uv run pytest tests/test_fast_scorer.py tests/test_trained_scorer.py tests/test_live_runtime_entry.py tests/test_signoz_first_routing.py` → `10 passed`
- `uv run pytest tests/test_signoz_primary_bundle.py tests/test_investigator_tools.py tests/test_live_investigation.py tests/test_markdown_builder.py tests/test_signoz_first_report.py tests/test_signoz_first_routing.py` → `16 passed`
- `uv run pytest tests/test_live_runtime_entry.py tests/test_live_signoz_runtime.py tests/test_bootstrap.py` → `13 passed`

### full regression
- `uv run pytest` → `113 passed`
- `uv run ruff check app tests scripts` → pass

### direct real probes
- direct Signoz-first decision probe against `prod-hq-bff-service` yielded:
  - `severity_band = P3`
  - `severity_score = 0.6`
  - `needs_investigation = True`
  - Signoz-primary reason codes including `signoz_alert_firing`
- direct Signoz-first investigation probe against `prod-hq-bff-service` yielded:
  - `route_should_investigate = True`
  - trace ids present
  - trace-detail hints present
  - Signoz-first report strings present
- direct live smoke:
  - `uv run python scripts/run_live_signoz_alert_smoke.py`
  - produced packet / decision / investigation / report with `candidate_source = signoz_alert`

## 4. Honest residuals

1. **live logs-by-trace is still best-effort**
   - current SigNoz environment may fail open on logs-by-trace correlation
   - runtime keeps working when that happens
2. **real smoke can still escalate to `cloud_fallback`**
   - current low-confidence cloud-fallback policy may still trigger after local-primary
   - this is a runtime-quality residual, not a source-priority residual
3. **Prometheus refs still appear in packets/reports as corroboration refs**
   - this is intentional
   - they are no longer the primary warning / severity / investigation truth

## 5. Honest claim boundary after closeout

warning-agent can now honestly claim:

> a Signoz alert can act as the primary runtime input, and warning-agent can build a Signoz-first packet,
> score it with Signoz-primary severity logic, investigate it with Signoz-first evidence, and render a Signoz-first report,
> while retaining Prometheus only as optional infra corroboration.

warning-agent should **not** yet claim:

- guaranteed logs-by-trace availability in the live environment
- guaranteed local-primary-only closeout for every live Signoz case under current cloud-fallback policy

## 6. Successor need

No mandatory successor pack is required for source-priority truth.

Optional future work may revisit:

- cloud-fallback thresholds for Signoz-first local-primary investigations
- more reliable logs-by-trace correlation
- a dedicated HTTP ingestion surface for live SigNoz alert pushes if/when needed
