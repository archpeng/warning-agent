# warning-agent Schema Draft

- Status: draft-contract
- Scope:
  - `incident packet`
  - `local analyzer decision`
  - `alert report` Markdown contract
- Intended outputs:
  - `schemas/incident-packet.v1.json`
  - `schemas/local-analyzer-decision.v1.json`
  - `schemas/alert-report-frontmatter.v1.json`

## 1. Contract Rules

1. All runtime contracts are versioned.
2. All timestamps use RFC3339 UTC strings.
3. The hot path must emit structured records first and prose second.
4. Every object must contain stable identifiers for replay and diffing.
5. The Markdown report is generated from schema fields; it is not the source of truth.

---

## 2. `incident-packet.v1`

### 2.1 Purpose

`incident packet` is the canonical runtime unit passed from evidence collection to local analysis and cloud investigation.

### 2.2 Top-level fields

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `schema_version` | string | yes | exact value `incident-packet.v1` | version pin |
| `packet_id` | string | yes | pattern `^ipk_[a-z0-9_\\-]+$` | stable packet id |
| `candidate_source` | string | yes | enum `alertmanager_webhook`, `prometheus_scan`, `manual_replay` | source of candidate creation |
| `created_at` | string | yes | RFC3339 UTC | packet creation time |
| `environment` | string | yes | non-empty | usually `prod`, `staging` |
| `service` | string | yes | non-empty | canonical service name |
| `operation` | string or null | yes | nullable | operation or endpoint |
| `entity_type` | string | yes | enum `service`, `service_operation` | packet grain |
| `entity_key` | string | yes | non-empty | stable key for retrieval and joins |
| `window` | object | yes | see below | bounded time window |
| `prometheus` | object | yes | see below | metric evidence |
| `signoz` | object | yes | see below | log and trace evidence |
| `topology` | object | yes | see below | routing and blast radius context |
| `history` | object | no | see below | optional historical context |
| `evidence_refs` | object | yes | see below | traceable evidence handles |

### 2.3 `window`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `start_ts` | string | yes | RFC3339 UTC |
| `end_ts` | string | yes | RFC3339 UTC |
| `duration_sec` | integer | yes | `>= 60` and `<= 3600` |

### 2.4 `prometheus`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `alerts_firing` | array of string | yes | may be empty |
| `error_rate` | number or null | yes | `>= 0` when present |
| `error_rate_baseline` | number or null | yes | `>= 0` when present |
| `error_rate_delta` | number or null | yes | nullable |
| `latency_p95_ms` | number or null | yes | `>= 0` when present |
| `latency_p95_baseline_ms` | number or null | yes | `>= 0` when present |
| `latency_p95_delta` | number or null | yes | nullable |
| `qps` | number or null | yes | `>= 0` when present |
| `qps_baseline` | number or null | yes | `>= 0` when present |
| `qps_delta` | number or null | yes | nullable |
| `saturation` | number or null | yes | `>= 0` when present |

### 2.5 `signoz`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `top_error_templates` | array of object | yes | max `10` items |
| `top_slow_operations` | array of object | yes | max `10` items |
| `trace_error_ratio` | number or null | yes | range `0.0` to `1.0` when present |
| `sample_trace_ids` | array of string | yes | may be empty |
| `sample_log_refs` | array of string | yes | may be empty |

#### `top_error_templates[]`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `template_id` | string | yes | non-empty |
| `template` | string | yes | non-empty |
| `count` | integer | yes | `>= 1` |
| `novelty_score` | number | yes | range `0.0` to `1.0` |

#### `top_slow_operations[]`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `operation` | string | yes | non-empty |
| `p95_ms` | number | yes | `>= 0` |
| `error_ratio` | number or null | yes | range `0.0` to `1.0` when present |

### 2.6 `topology`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `tier` | string | yes | enum `tier0`, `tier1`, `tier2`, `unknown` |
| `owner` | string or null | yes | nullable |
| `repo_candidates` | array of string | yes | may be empty |
| `upstream_count` | integer | yes | `>= 0` |
| `downstream_count` | integer | yes | `>= 0` |
| `blast_radius_score` | number | yes | range `0.0` to `1.0` |

### 2.7 `history`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `recent_deploy` | boolean | no | default `false` |
| `similar_incident_ids` | array of string | no | may be empty |
| `similar_packet_ids` | array of string | no | may be empty |

### 2.8 `evidence_refs`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `prometheus_query_refs` | array of string | yes | may be empty |
| `signoz_query_refs` | array of string | yes | may be empty |

### 2.9 Example

```json
{
  "schema_version": "incident-packet.v1",
  "packet_id": "ipk_checkout_post_pay_20260418t120000z",
  "candidate_source": "alertmanager_webhook",
  "created_at": "2026-04-18T12:00:08Z",
  "environment": "prod",
  "service": "checkout",
  "operation": "POST /api/pay",
  "entity_type": "service_operation",
  "entity_key": "checkout:POST /api/pay",
  "window": {
    "start_ts": "2026-04-18T11:55:00Z",
    "end_ts": "2026-04-18T12:00:00Z",
    "duration_sec": 300
  },
  "prometheus": {
    "alerts_firing": ["high_error_rate", "latency_p95_high"],
    "error_rate": 0.21,
    "error_rate_baseline": 0.02,
    "error_rate_delta": 0.19,
    "latency_p95_ms": 2400,
    "latency_p95_baseline_ms": 410,
    "latency_p95_delta": 1990,
    "qps": 122,
    "qps_baseline": 118,
    "qps_delta": 4,
    "saturation": 0.81
  },
  "signoz": {
    "top_error_templates": [
      {
        "template_id": "tmpl_db_timeout",
        "template": "db timeout on order lookup",
        "count": 182,
        "novelty_score": 0.91
      }
    ],
    "top_slow_operations": [
      {
        "operation": "POST /api/pay",
        "p95_ms": 2400,
        "error_ratio": 0.34
      }
    ],
    "trace_error_ratio": 0.34,
    "sample_trace_ids": ["7f8a3c", "7f8a40"],
    "sample_log_refs": ["signoz://logs/query-123/row-18"]
  },
  "topology": {
    "tier": "tier1",
    "owner": "payments-oncall",
    "repo_candidates": ["checkout-service", "payment-gateway-client"],
    "upstream_count": 6,
    "downstream_count": 12,
    "blast_radius_score": 0.88
  },
  "history": {
    "recent_deploy": true,
    "similar_incident_ids": ["INC-1422"],
    "similar_packet_ids": ["ipk_checkout_post_pay_20260411t110000z"]
  },
  "evidence_refs": {
    "prometheus_query_refs": ["prom://query/high_error_rate_window_300s"],
    "signoz_query_refs": ["signoz://trace/query-123", "signoz://logs/query-456"]
  }
}
```

---

## 3. `local-analyzer-decision.v1`

### 3.1 Purpose

This object is the only output contract of the local dense analyzer, regardless of whether the backend is a fast scorer or a local small model.

### 3.2 Top-level fields

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `schema_version` | string | yes | exact value `local-analyzer-decision.v1` | version pin |
| `decision_id` | string | yes | pattern `^lad_[a-z0-9_\\-]+$` | stable decision id |
| `packet_id` | string | yes | pattern `^ipk_[a-z0-9_\\-]+$` | join back to packet |
| `analyzer_family` | string | yes | enum `fast_scorer`, `small_model`, `hybrid` | implementation family |
| `analyzer_version` | string | yes | non-empty | model or scorer version |
| `severity_band` | string | yes | enum `P1`, `P2`, `P3`, `P4` | final local severity band |
| `severity_score` | number | yes | range `0.0` to `1.0` | dense risk score |
| `novelty_score` | number | yes | range `0.0` to `1.0` | novelty or unfamiliarity |
| `confidence` | number | yes | range `0.0` to `1.0` | local confidence |
| `needs_cloud_investigation` | boolean | yes | exact boolean | sparse escalation gate |
| `recommended_action` | string | yes | enum `observe`, `open_ticket`, `page_owner`, `send_to_human_review` | local action candidate |
| `reason_codes` | array of string | yes | min `1`, max `8` | structured explanation surface |
| `risk_flags` | array of string | yes | may be empty | high-risk markers |
| `retrieval_hits` | array of object | yes | max `5` items | local search evidence |
| `cloud_trigger_reasons` | array of string | yes | empty when not escalated | why cloud investigation is needed |

### 3.3 `risk_flags`

Allowed values:

- `rule_miss`
- `high_blast_radius`
- `new_template`
- `owner_unknown`
- `recent_deploy`
- `service_hotspot`

### 3.4 `retrieval_hits[]`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `packet_id` | string | yes | non-empty |
| `similarity` | number | yes | range `0.0` to `1.0` |
| `known_outcome` | string | yes | enum `severe`, `benign`, `unknown` |

### 3.5 Validation rules

1. If `needs_cloud_investigation = false`, `cloud_trigger_reasons` must be empty.
2. If `recommended_action = page_owner`, `severity_band` must be `P1` or `P2`.
3. If `confidence < 0.35`, `needs_cloud_investigation` should normally be `true`.
4. `reason_codes` must be machine-aggregatable strings, not prose sentences.

### 3.6 Example

```json
{
  "schema_version": "local-analyzer-decision.v1",
  "decision_id": "lad_checkout_post_pay_20260418t120010z",
  "packet_id": "ipk_checkout_post_pay_20260418t120000z",
  "analyzer_family": "fast_scorer",
  "analyzer_version": "fast-scorer-2026-04-18",
  "severity_band": "P1",
  "severity_score": 0.94,
  "novelty_score": 0.87,
  "confidence": 0.61,
  "needs_cloud_investigation": true,
  "recommended_action": "page_owner",
  "reason_codes": [
    "error_rate_spike",
    "template_novelty_high",
    "similar_to_past_severe"
  ],
  "risk_flags": [
    "high_blast_radius",
    "recent_deploy"
  ],
  "retrieval_hits": [
    {
      "packet_id": "ipk_checkout_post_pay_20260411t110000z",
      "similarity": 0.82,
      "known_outcome": "severe"
    }
  ],
  "cloud_trigger_reasons": [
    "novelty_high",
    "blast_radius_high"
  ]
}
```

---

## 4. `alert-report.v1`

### 4.1 Purpose

This is the stable Markdown product output. It must be generated from packet fields, local decision fields, and optional cloud investigation fields.

### 4.2 Frontmatter contract

The report must begin with YAML frontmatter.

Required fields:

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema_version` | string | yes | exact value `alert-report.v1` |
| `report_id` | string | yes | pattern `^rpt_[a-z0-9_\\-]+$` |
| `packet_id` | string | yes | pattern `^ipk_[a-z0-9_\\-]+$` |
| `decision_id` | string | yes | pattern `^lad_[a-z0-9_\\-]+$` |
| `generated_at` | string | yes | RFC3339 UTC |
| `severity_band` | string | yes | enum `P1`, `P2`, `P3`, `P4` |
| `delivery_class` | string | yes | enum `observe`, `open_ticket`, `page_owner`, `send_to_human_review` |
| `cloud_investigation_used` | boolean | yes | exact boolean |
| `service` | string | yes | non-empty |
| `operation` | string or null | yes | nullable |
| `owner` | string or null | yes | nullable |
| `repo_candidates` | array of string | yes | may be empty |
| `prometheus_ref_ids` | array of string | yes | may be empty |
| `signoz_ref_ids` | array of string | yes | may be empty |

### 4.3 Body section contract

The Markdown body must contain the following section headers in exact order:

1. `## Executive Summary`
2. `## Why This Alert Exists`
3. `## Metric Signals`
4. `## Logs And Traces`
5. `## Cloud Investigation`
6. `## Impact And Routing`
7. `## Recommended Action`
8. `## Evidence Refs`
9. `## Unknowns`

### 4.4 Section requirements

#### `## Executive Summary`

Must contain flat bullets for:

- service
- operation
- window
- severity band
- confidence
- delivery class

#### `## Why This Alert Exists`

Must contain:

- local analyzer reason codes
- local novelty and confidence summary
- cloud trigger reasons or explicit `none`

#### `## Metric Signals`

Must contain:

- firing alerts
- error rate delta
- p95 delta
- qps delta
- saturation when present

#### `## Logs And Traces`

Must contain:

- top error templates
- trace error ratio
- top slow operations

#### `## Cloud Investigation`

If `cloud_investigation_used = true`, this section must contain:

- suspected failure chain
- likely impacted repo or module
- key code confirmation refs

If `cloud_investigation_used = false`, this section must contain exactly one bullet:

- `not used`

#### `## Impact And Routing`

Must contain:

- blast radius summary
- owner
- repo candidates

#### `## Recommended Action`

Must contain:

- immediate action
- next checks
- escalation target

#### `## Evidence Refs`

Must contain:

- Prometheus refs
- SigNoz refs
- code refs when present

#### `## Unknowns`

Must contain at least one bullet.

If there are no material unknowns, use:

- `none`

### 4.5 Frontmatter example

```yaml
---
schema_version: alert-report.v1
report_id: rpt_checkout_post_pay_20260418t120030z
packet_id: ipk_checkout_post_pay_20260418t120000z
decision_id: lad_checkout_post_pay_20260418t120010z
generated_at: 2026-04-18T12:00:30Z
severity_band: P1
delivery_class: page_owner
cloud_investigation_used: true
service: checkout
operation: POST /api/pay
owner: payments-oncall
repo_candidates:
  - checkout-service
  - payment-gateway-client
prometheus_ref_ids:
  - prom://query/high_error_rate_window_300s
signoz_ref_ids:
  - signoz://trace/query-123
  - signoz://logs/query-456
---
```

### 4.6 Markdown body example

```md
## Executive Summary
- service: `checkout`
- operation: `POST /api/pay`
- window: `2026-04-18T11:55:00Z -> 2026-04-18T12:00:00Z`
- severity band: `P1`
- confidence: `0.61`
- delivery class: `page_owner`

## Why This Alert Exists
- local reason codes: `error_rate_spike`, `template_novelty_high`, `similar_to_past_severe`
- local summary: `novelty=0.87 confidence=0.61`
- cloud trigger reasons: `novelty_high`, `blast_radius_high`

## Metric Signals
- firing alerts: `high_error_rate`, `latency_p95_high`
- error rate delta: `+0.19`
- p95 delta ms: `+1990`
- qps delta: `+4`
- saturation: `0.81`

## Logs And Traces
- top template: `db timeout on order lookup` count=`182` novelty=`0.91`
- trace error ratio: `0.34`
- top slow op: `POST /api/pay` p95=`2400`

## Cloud Investigation
- suspected failure chain: `checkout -> payment gateway lookup -> db timeout burst`
- likely repo or module: `checkout-service/payment lookup path`
- code refs: `[checkout/payment_client.py:88]`

## Impact And Routing
- blast radius: `0.88`
- owner: `payments-oncall`
- repo candidates: `checkout-service`, `payment-gateway-client`

## Recommended Action
- immediate action: `page_owner`
- next checks: `confirm payment gateway error budget and recent deploy`
- escalation target: `payments-oncall`

## Evidence Refs
- Prometheus: `prom://query/high_error_rate_window_300s`
- SigNoz: `signoz://trace/query-123`, `signoz://logs/query-456`
- Code: `[checkout/payment_client.py:88]`

## Unknowns
- whether the timeout burst originated from the database tier or the upstream payment gateway
```

---

## 5. Final Rule

The runtime source of truth is:

`incident packet` + `local analyzer decision` + optional cloud investigation record

The Markdown report is a stable projection of those objects.
