# warning-agent Architecture

- Status: draft-ssot
- Scope: narrow smart-alerting product for `Prometheus + SigNoz`
- Design anchor: `../theBitterLessons.md`
- Product target:
  - accept realtime alerts from Prometheus and deep-link into SigNoz evidence
  - run high-frequency local analysis to produce a reliable first-pass result
  - escalate only suspicious high-risk cases to a cloud LLM for deep investigation
  - emit a stable Markdown alert report as the product output

## 1. Product Goal

The product goal is intentionally narrow:

1. Receive alert signals and collect bounded evidence from `Prometheus` and `SigNoz`.
2. Convert that evidence into one compact canonical unit.
3. Run cheap local search and learning over that unit at high frequency.
4. Escalate only a small subset of hard cases to a cloud investigator.
5. Produce one stable Markdown alert report.

The product is not:

- a full observability UI
- a full incident autopilot
- a general multi-agent platform
- a raw-log reader that lets the cloud model scan everything

## 2. Bitter Lesson Design Laws

`theBitterLessons.md` points to two methods that continue to scale: `search` and `learning`.

For this product that means:

1. Build one compact machine-readable event representation first.
2. Use local search over historical packets and reports before asking for free-form reasoning.
3. Use local learning for dense first-pass scoring instead of growing service-specific rules.
4. Use the cloud LLM only as a sparse investigator, not as the always-on first-pass engine.
5. Keep outputs structured so they can be searched, learned from, and replayed later.
6. Feed outcomes back into the local analyzer instead of adding more handcrafted heuristics.

Anti-patterns under this philosophy:

- service-by-service prompt branches
- long handcrafted reasoning trees in the hot path
- raw logs as the canonical decision unit
- using the cloud LLM for every alert
- writing Markdown as free-form prose without stable sections

## 3. Canonical Unit

The only canonical runtime unit should be the `incident packet`.

Why:

- it compresses bounded telemetry into a searchable unit
- it is cheap to store and replay
- it is the right input for both local learning and cloud investigation
- it prevents the system from turning into "LLM reads arbitrary logs"

Everything downstream should consume `incident packet`, not raw observability streams.

## 4. Smallest Viable System

The smallest correct system has six online components and two offline loops.

| Layer | Component | Responsibility | Hot path? |
|---|---|---|---|
| Input | Alert Receiver | Accept Alertmanager webhook events and optional hot-window scans | yes |
| Evidence | Evidence Collector | Run fixed Prometheus and SigNoz queries for one bounded time window | yes |
| Canonicalization | Incident Packet Builder | Convert evidence into one packet | yes |
| Dense Local Compute | Local Analyzer | Run retrieval plus a fast scorer and return structured decision signals | yes |
| Sparse Expensive Compute | Cloud Investigator | Investigate only escalated packets using bounded tools | no |
| Output | Markdown Report Builder | Render one stable alert report | yes |
| Feedback | Outcome Store | Save packets, decisions, reports, and operator outcomes | offline |
| Learning | Retrain / Recalibrate Jobs | Refresh retrieval index and local analyzer weights | offline |

This is enough to build the product.

Everything below is intentionally excluded from the minimum structure:

- action autopilot
- runtime action admission
- promotion ladder
- temporal sidecar
- multi-lane automation
- complex memory substrate

## 5. Runtime Flow

### 5.1 Fast path

```text
Alertmanager webhook
  -> bounded evidence collection
  -> incident packet
  -> local retrieval
  -> local scorer
  -> structured local decision
  -> markdown alert report
```

Use this when:

- confidence is high enough
- novelty is low enough
- blast radius is below the escalation bar

### 5.2 Deep investigation path

```text
incident packet
  -> local analyzer says "needs cloud investigation"
  -> cloud investigator
  -> bounded Signoz MCP analysis
  -> bounded Prometheus follow-up
  -> repo code confirmation on mapped repos only
  -> enriched markdown alert report
```

Use this when:

- confidence is low
- novelty is high
- blast radius is high
- local score conflicts with fired alerts or retrieval context

### 5.3 Feedback path

```text
report + operator action + incident outcome
  -> feedback store
  -> retrieval refresh
  -> local analyzer recalibration
  -> later local model fine-tuning
```

This is the only sustainable way to improve the product under the Bitter Lesson.

## 6. Recommended Technical Path

The simplest path that still follows the Bitter Lesson is:

### Stage A: packet-first baseline

- Alertmanager webhook as the main realtime entrypoint
- fixed Prometheus query bundle
- fixed SigNoz query bundle
- packet builder
- Markdown report template

No local LLM yet. No cloud LLM in the hot path yet.

### Stage B: search-first local analyzer

- render packet into compact text
- build a local retrieval index over:
  - historical packets
  - historical alert reports
  - historical outcomes
- use a fast local scorer on top of:
  - packet numeric features
  - packet categorical features
  - retrieval outputs

Recommended first implementation:

- retrieval: `SQLite FTS5` or `BM25` over packet render text plus exact service/operation filters
- scorer: `Logistic Regression`, `LightGBM`, or another cheap classifier/ranker

This is already a valid "local script" analyzer and is more Bitter-Lesson-aligned than jumping straight to a local chat model.

### Stage C: sparse cloud investigator

Keep the cloud model bounded.

Inputs:

- one packet
- one local analyzer decision
- a small retrieval summary
- optional repo list from topology mapping

Allowed tools:

- `SigNoz MCP` for traces, logs, and aggregates
- bounded Prometheus follow-up queries
- repo code search only in mapped candidate repos

Forbidden behavior:

- scanning full raw log floods
- searching arbitrary repos without mapping
- replacing the local first-pass scorer

### Stage D: local small model upgrade

Only after the previous stages work end-to-end:

- keep the same `local analyzer` output contract
- swap the cheap scorer for a small text-first model behind the same interface
- train on packet render plus outcome-backed labels
- distill from cloud investigator outputs only where that creates measurable gain

This is the right place for the local small model.

## 7. Why the Local Analyzer Should Not Start as a Chat Agent

If the local analyzer starts as a free-form local agent, the design drifts away from the Bitter Lesson:

- less searchable
- less replayable
- less calibratable
- harder to benchmark
- harder to improve with more data

The hot path should therefore stay:

`search + structured learning -> structured decision`

not:

`prompt + prose + hidden reasoning`

The local analyzer may internally use a small model later, but the product contract should remain structured.

## 8. Recommended Model Split

Use this split:

| Layer | Role | Requirement |
|---|---|---|
| Local analyzer | dense first-pass triage | cheap, fast, structured, rollback-friendly |
| Cloud investigator | sparse deep investigation | tool-using, cross-signal reasoning, repo confirmation |

Local analyzer outputs:

- `severity_band`
- `severity_score`
- `novelty_score`
- `confidence`
- `needs_cloud_investigation`
- `recommended_action`
- `reason_codes`

Cloud investigator outputs:

- suspected failure chain
- confidence-adjusted severity update
- likely impacted owner and repo
- next verification steps
- unresolved unknowns

This is the simplest useful split.

## 9. Minimal Storage Model

Do not start with a distributed data platform.

Use:

- `SQLite` for decision, report, and outcome metadata
- `JSONL` or `Parquet` for packet and replay artifacts
- local search index files for retrieval

Minimum persistent entities:

- `incident_packets`
- `local_decisions`
- `cloud_investigations`
- `alert_reports`
- `operator_outcomes`

That is enough for replay, calibration, and later training.

## 10. Evaluation Bars

The minimum useful evaluation loop should track:

- severe recall
- top-K precision
- cloud escalation rate
- false-page rate
- local analyzer latency
- report completeness rate

If a future local small model does not improve the combination of:

- severe recall
- top-K precision
- cloud escalation rate
- latency

then it should not replace the simpler scorer.

## 11. Markdown Report as Product Output

The report is not a side artifact. It is the product.

Every alert should end as one stable Markdown document with:

- executive summary
- key metric signals
- key logs and traces
- why it escalated
- cloud investigation result or explicit "not used"
- impact and routing
- recommended action
- evidence references
- unknowns

The report must be generated from stable fields, not from uncontrolled prose.

## 12. Final Recommendation

If the goal is only:

- fast local analysis
- sparse cloud investigation
- Markdown alert reports

then the simplest correct architecture is:

```text
Alert receiver
  -> evidence collector
  -> incident packet
  -> retrieval + local analyzer
  -> optional cloud investigator
  -> markdown report
  -> outcome feedback
```

This is the narrowest product that still fully follows the Bitter Lesson:

- one canonical unit
- one dense local search-and-learning path
- one sparse expensive reasoning path
- one stable output contract
- one feedback loop
