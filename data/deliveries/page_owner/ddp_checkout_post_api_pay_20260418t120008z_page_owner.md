---
schema_version: alert-report.v1
report_id: rpt_checkout_post_api_pay_20260418t120008z
packet_id: ipk_checkout_post_api_pay_20260418t120008z
decision_id: lad_checkout_post_pay_20260418t120010z
generated_at: '2026-04-18T12:00:24Z'
severity_band: P1
delivery_class: page_owner
investigation_stage: cloud_fallback
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

## Executive Summary
- service: `checkout`
- operation: `POST /api/pay`
- window: `2026-04-18T11:55:00Z -> 2026-04-18T12:00:00Z`
- severity band: `P1`
- confidence: `0.77`
- delivery class: `page_owner`

## Why This Alert Exists
- local reason codes: `error_rate_spike`, `template_novelty_high`
- local summary: `novelty=0.91 confidence=0.55`
- investigation trigger reasons: `novelty_high`, `blast_radius_high`

## Metric Signals
- firing alerts: `high_error_rate`, `latency_p95_high`
- error rate delta: `0.19`
- p95 delta ms: `1990`
- qps delta: `4`
- saturation: `0.81`

## Logs And Traces
- top template: `db timeout on order lookup` count=`182` novelty=`0.91`
- trace error ratio: `0.34`
- top slow op: `POST /api/pay` p95=`2400`

## Investigation
- suspected primary cause: `db timeout on order lookup`
- suspected failure chain: `cloud fallback reviewed the bounded local handoff for checkout POST /api/pay and retained db timeout on order lookup as the leading failure chain driver.`
- top hypothesis: `cloud fallback confirms db timeout on order lookup as the most likely driver of the checkout regression on POST /api/pay`
- likely repo or module: `checkout-service`, `payment-gateway-client`
- code refs: `services/checkout/post_api_pay.py`, `repos/checkout-service/post_api_pay`

## Impact And Routing
- blast radius: `0.88`
- owner: `payments-oncall`
- repo candidates: `checkout-service`, `payment-gateway-client`

## Recommended Action
- immediate action: `page_owner`
- next checks: `bounded local follow-up used repo_search only; live metric/log follow-up remains pending`, `deterministic cloud fallback smoke client is active; live vendor API integration remains pending`
- escalation target: `payments-oncall`

## Evidence Refs
- Prometheus: `prom://query/high_error_rate_window_300s`
- SigNoz: `signoz://trace/query-123`, `signoz://logs/query-456`
- Code: `services/checkout/post_api_pay.py`, `repos/checkout-service/post_api_pay`

## Unknowns
- bounded local follow-up used repo_search only; live metric/log follow-up remains pending
- deterministic cloud fallback smoke client is active; live vendor API integration remains pending
