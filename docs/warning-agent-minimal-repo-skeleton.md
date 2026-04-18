# warning-agent Minimal Repo Skeleton

- Status: draft
- Scope: smallest repository layout for the narrow smart-alerting product
- Depends on:
  - `warning-agent-architecture.md`
  - `warning-agent-schema-draft.md`

## 1. Design Goal

The repository should make the hot path obvious and keep everything else out.

The hot path is:

```text
alert -> packet -> local analysis -> optional cloud investigation -> markdown report
```

The repository should not contain:

- action autopilot code
- promotion ladder code
- temporal sidecar code
- multi-service governance frameworks
- large UI surfaces

## 2. Minimal Tree

```text
warning-agent/
  docs/
    warning-agent-architecture.md
    warning-agent-minimal-repo-skeleton.md
    warning-agent-schema-draft.md

  app/
    main.py

    receiver/
      alertmanager_webhook.py
      hot_window_scan.py

    collectors/
      prometheus.py
      signoz.py

    packet/
      builder.py
      render.py
      contracts.py

    retrieval/
      index.py
      search.py

    analyzer/
      base.py
      fast_scorer.py
      small_model.py
      calibrate.py

    investigator/
      cloud_investigator.py
      signoz_tools.py
      prom_tools.py
      repo_locator.py

    reports/
      markdown_builder.py
      templates.py

    storage/
      sqlite_store.py
      artifact_store.py

    feedback/
      outcome_ingest.py
      retrain_jobs.py

  schemas/
    incident-packet.v1.json
    local-analyzer-decision.v1.json
    alert-report-frontmatter.v1.json

  configs/
    services.yaml
    thresholds.yaml
    escalation.yaml
    reports.yaml

  data/
    packets/
    decisions/
    investigations/
    reports/
    outcomes/
    retrieval/

  scripts/
    run_shadow_replay.py
    rebuild_retrieval_index.py
    train_fast_scorer.py
    train_small_model.py
    backfill_packets.py

  tests/
    test_packet_builder.py
    test_retrieval.py
    test_fast_scorer.py
    test_cloud_investigator.py
    test_markdown_builder.py
    test_end_to_end_shadow.py
```

## 3. File Responsibilities

| Path | Must exist now? | Responsibility |
|---|---|---|
| `app/receiver/alertmanager_webhook.py` | yes | accept Alertmanager events and enqueue bounded analysis jobs |
| `app/collectors/prometheus.py` | yes | collect fixed Prometheus metric windows |
| `app/collectors/signoz.py` | yes | collect fixed SigNoz log and trace evidence |
| `app/packet/builder.py` | yes | build canonical `incident packet` objects |
| `app/packet/render.py` | yes | render packet text for retrieval and local model input |
| `app/retrieval/index.py` | yes | build local search index over packets, reports, and outcomes |
| `app/retrieval/search.py` | yes | return top historical matches for one packet |
| `app/analyzer/fast_scorer.py` | yes | run cheap local first-pass scoring |
| `app/analyzer/small_model.py` | later | drop-in local small-model implementation behind the same analyzer contract |
| `app/investigator/cloud_investigator.py` | yes | bounded cloud investigation for escalated packets |
| `app/investigator/repo_locator.py` | yes | map packet service or operation to candidate repos before code search |
| `app/reports/markdown_builder.py` | yes | generate the stable Markdown alert report |
| `app/storage/sqlite_store.py` | yes | store metadata for packets, decisions, reports, and outcomes |
| `app/storage/artifact_store.py` | yes | read and write JSONL or Parquet artifacts |
| `app/feedback/outcome_ingest.py` | yes | ingest operator or incident outcomes |
| `app/feedback/retrain_jobs.py` | later | rebuild retrieval and refresh local analyzer weights |

## 4. Suggested Build Order

Build the repository in this order:

1. `schemas/`
2. `packet/`
3. `collectors/`
4. `reports/`
5. `retrieval/`
6. `analyzer/fast_scorer.py`
7. `investigator/`
8. `feedback/`
9. `analyzer/small_model.py`

This order preserves the Bitter Lesson logic:

- first make the representation stable
- then make search work
- then add cheap local learning
- only then add a local small model behind the same contract

## 5. Hot Path vs Offline Path

### Hot path modules

These must stay simple and deterministic:

- `receiver/*`
- `collectors/*`
- `packet/*`
- `retrieval/search.py`
- `analyzer/fast_scorer.py`
- `investigator/cloud_investigator.py`
- `reports/markdown_builder.py`

### Offline path modules

These can evolve later:

- `retrieval/index.py`
- `feedback/retrain_jobs.py`
- `scripts/train_fast_scorer.py`
- `scripts/train_small_model.py`

## 6. Local Analyzer Contract Boundary

The repository should treat local analysis as one stable interface:

- input: `incident packet`
- output: `local analyzer decision`

Two implementations may live behind that interface:

1. `fast_scorer.py`
   - current default
   - cheap, high-frequency
   - retrieval plus structured scorer
2. `small_model.py`
   - later replacement candidate
   - same output schema
   - same metrics and rollback bars

This prevents the repository from coupling product behavior to one model family.

## 7. Cloud Investigator Boundary

The cloud investigator must stay a sidecar, not the main runtime brain.

It may:

- read one packet
- read one local analyzer decision
- call SigNoz and Prometheus tools
- search mapped repos only
- write one investigation result

It may not:

- act as the first-pass scorer
- scan arbitrary raw logs at global scale
- decide product output format on its own

## 8. Storage Layout

Prefer simple local storage first.

Recommended default:

- `SQLite` for metadata tables
- `JSONL` for raw packet, decision, investigation, and outcome artifacts
- local on-disk retrieval index

Suggested table set:

- `packets`
- `local_decisions`
- `cloud_investigations`
- `alert_reports`
- `outcomes`

## 9. Configuration Files

Keep configuration small and explicit.

### `services.yaml`

Contains:

- service names
- operation allowlists if needed
- owner hints
- repo hints

### `thresholds.yaml`

Contains:

- local severity thresholds
- novelty threshold
- cloud escalation threshold
- false-page guardrails

### `escalation.yaml`

Contains:

- cloud investigation trigger rules
- max concurrent investigations
- report delivery rules

### `reports.yaml`

Contains:

- Markdown section order
- severity-to-delivery mapping
- optional report labels

## 10. Deliberately Missing From This Skeleton

These are intentionally not part of the minimal repository:

- UI server
- workflow engine
- action execution sink
- autopilot ledgers
- promotion-state artifacts
- temporal experiments
- multi-tenant control plane

If any of these become necessary, they should be justified by product evidence first.

## 11. Final Recommendation

This repository skeleton is intentionally narrower than `fixit`.

It is built for one thing:

`realtime smart alerting with cheap local first-pass analysis and sparse cloud investigation`

If a new file or module does not directly support that loop, it should not enter the repository.
