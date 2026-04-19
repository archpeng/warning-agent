# warning-agent Signoz-First Runbook

- status: `active-runbook-ssot`
- scope:
  - Signoz-first warning input
  - Signoz-first severity and investigation evidence
  - Prometheus corroboration-only policy

## 1. Source priority freeze

Current source priority is:

1. **SigNoz alert** = primary warning input
2. **SigNoz traces / top operations / trace details** = primary severity + investigation evidence
3. **Prometheus** = optional infra corroboration only

This is a hard freeze for the active successor workstream.

## 2. What Prometheus may still do

Prometheus is still allowed to provide:

- pod readiness / availability corroboration
- restart / saturation / CPU / memory style corroboration
- secondary signal when SigNoz evidence is incomplete

Prometheus is **not** the primary future target for:

- warning input
- severity ranking
- investigation justification
- service-by-service query family expansion

## 3. What Signoz must provide

The Signoz-first plane should treat the following as primary truth:

- firing alert identity
- service / endpoint / operation
- error count / error ratio / failing traces
- trace hierarchy
- downstream dependency / target service hints
- status codes / response codes
- top failing or slow operations

## 4. Honest boundary

The Signoz-first workstream is complete only when warning-agent can honestly say:

> the primary warning source is SigNoz, and the primary severity + investigation evidence is also SigNoz;
> Prometheus is retained only as optional infra corroboration.

Until then, mixed live-data MVP behavior remains historical predecessor truth, not the target source-priority truth.

## 5. Runtime invocation

The Signoz-first runtime entry now supports:

- CLI: `warning-agent signoz-alert fixtures/replay/signoz-alert.prod-hq-bff-service.error.json`
- smoke script: `uv run python scripts/run_live_signoz_alert_smoke.py`

This path uses:

- raw SigNoz alert fixture / payload as input
- Signoz-first evidence bundle materialization
- Signoz-first analyzer + routing
- Signoz-first investigation / report rendering

## 6. Honest residuals

Current closeout residuals are:

- live logs-by-trace correlation is still best-effort and may fail open
- the current real smoke can still escalate to `cloud_fallback` under existing low-confidence policy,
  even though the primary packet / decision / investigation / report evidence is Signoz-first

These residuals do not change the source-priority truth; they only bound the current runtime behavior.

## 7. Predecessor note

The predecessor document `docs/warning-agent-live-data-mvp-runbook.md` remains useful as a historical MVP baseline,
but it is no longer the authoritative source-priority document for current work.
