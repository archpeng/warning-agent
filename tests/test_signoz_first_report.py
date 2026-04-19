from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.signoz_alert import normalize_signoz_alert_payload
from app.reports.contracts import BODY_SECTION_ORDER, load_schema as load_report_schema
from app.reports.markdown_builder import render_alert_report


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_signoz_first_packet() -> dict[str, object]:
    normalized = normalize_signoz_alert_payload(
        {
            "alert": "signoz error",
            "state": "firing",
            "ruleId": "019d1fad-feb8-74c3-9610-dd894c6390d0",
            "serviceName": "prod-hq-bff-service",
            "endpoint": "POST /api/datamesh/v1/charts/data",
            "severity": "error",
            "evalWindow": "5m0s",
            "source": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
            "labels": {"environment": "prod", "severity": "error"},
            "annotations": {"summary": "current error rate crossed threshold"},
        }
    )
    bundle = {
        "created_at": "2026-04-19T10:00:00Z",
        "window": {
            "start_ts": "2026-04-19T09:55:00Z",
            "end_ts": "2026-04-19T10:00:00Z",
            "duration_sec": 300,
        },
        "prometheus": {
            "alerts_firing": [],
            "error_rate": None,
            "error_rate_baseline": None,
            "error_rate_delta": None,
            "latency_p95_ms": None,
            "latency_p95_baseline_ms": None,
            "latency_p95_delta": None,
            "qps": None,
            "qps_baseline": None,
            "qps_delta": None,
            "saturation": None,
        },
        "signoz": {
            "top_error_templates": [
                {
                    "template_id": "trace-log-1",
                    "template": "downstream dependency 503 timeout",
                    "count": 4,
                    "novelty_score": 0.82,
                }
            ],
            "top_slow_operations": [
                {
                    "operation": "POST /api/datamesh/v1/charts/data",
                    "p95_ms": 1800.0,
                    "error_ratio": 0.78,
                }
            ],
            "trace_error_ratio": 1.0,
            "sample_trace_ids": ["trace-1", "trace-2"],
            "sample_log_refs": ["signoz-mcp://log-row/trace-log-1"],
            "alert_context": {
                "rule_id": "019d1fad-feb8-74c3-9610-dd894c6390d0",
                "source_url": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
                "eval_window": "5m0s",
                "severity": "error",
            },
            "trace_detail_hints": [
                {
                    "trace_id": "trace-1",
                    "span_name": "grpc.center.CenterService/DeviceInfo",
                    "service_name": "g-center-service",
                    "target": "g-center-service",
                    "status_code": "503",
                }
            ],
        },
        "topology": {
            "tier": "tier1",
            "owner": "hq-oncall",
            "repo_candidates": ["hq-bff-service"],
            "upstream_count": 2,
            "downstream_count": 6,
            "blast_radius_score": 0.82,
        },
        "history": {
            "recent_deploy": False,
            "similar_incident_ids": [],
            "similar_packet_ids": [],
        },
        "evidence_refs": {
            "prometheus_query_refs": [],
            "signoz_query_refs": [
                "signoz-mcp://alert?rule_id=019d1fad-feb8-74c3-9610-dd894c6390d0",
                "signoz-mcp://trace_detail?trace_id=trace-1",
            ],
        },
    }
    return build_incident_packet_from_bundle(normalized, bundle)


def test_markdown_builder_renders_signoz_first_report_sections() -> None:
    packet = _build_signoz_first_packet()
    decision = {
        "schema_version": "local-analyzer-decision.v1",
        "decision_id": "lad_prod_hq_bff_service_post_api_datamesh_20260419t100002z",
        "packet_id": packet["packet_id"],
        "analyzer_family": "hybrid",
        "analyzer_version": "trained-scorer-2026-04-19",
        "severity_band": "P3",
        "severity_score": 0.6,
        "novelty_score": 0.82,
        "confidence": 0.42,
        "needs_investigation": True,
        "recommended_action": "open_ticket",
        "reason_codes": ["signoz_alert_firing", "error_rate_spike"],
        "risk_flags": ["high_blast_radius"],
        "retrieval_hits": [],
        "investigation_trigger_reasons": ["blast_radius_high", "confidence_low"],
    }
    investigation = {
        "schema_version": "investigation-result.v1",
        "investigation_id": "cir_prod_hq_bff_service_post_api_datamesh_20260419t100004z",
        "packet_id": packet["packet_id"],
        "decision_id": decision["decision_id"],
        "investigator_tier": "local_primary_investigator",
        "model_provider": "local_vllm",
        "model_name": "local-primary-smoke",
        "generated_at": "2026-04-19T10:00:04Z",
        "input_refs": {
            "packet_id": packet["packet_id"],
            "decision_id": decision["decision_id"],
            "retrieval_packet_ids": [],
            "prometheus_query_refs": [],
            "signoz_query_refs": packet["evidence_refs"]["signoz_query_refs"],
            "code_search_refs": [],
            "upstream_report_id": None,
        },
        "summary": {
            "investigation_used": True,
            "severity_band": "P3",
            "recommended_action": "open_ticket",
            "confidence": 0.56,
            "reason_codes": ["signoz_alert_firing", "error_rate_spike"],
            "suspected_primary_cause": "downstream dependency 503 timeout",
            "failure_chain_summary": "Signoz alert fired for POST /api/datamesh/v1/charts/data and trace detail points to g-center-service returning 503.",
        },
        "hypotheses": [
            {
                "rank": 1,
                "hypothesis": "g-center-service 503s are driving the prod-hq-bff-service regression",
                "confidence": 0.71,
                "supporting_reason_codes": ["signoz_alert_firing", "error_rate_spike"],
            }
        ],
        "analysis_updates": {
            "severity_band_changed": False,
            "recommended_action_changed": False,
            "fallback_invocation_was_correct": None,
            "notes": ["packet_signoz_alert_context_used", "live_signoz_trace_details_used"],
        },
        "routing": {
            "owner_hint": "hq-oncall",
            "repo_candidates": ["hq-bff-service"],
            "suspected_code_paths": ["hq-bff-service/device-detail"],
            "escalation_target": "hq-oncall",
        },
        "evidence_refs": {
            "prometheus_ref_ids": [],
            "signoz_ref_ids": packet["evidence_refs"]["signoz_query_refs"],
            "trace_ids": ["trace-1", "trace-2"],
            "code_refs": ["hq-bff-service/device-detail"],
        },
        "unknowns": ["Prometheus corroboration not required for primary diagnosis."],
    }

    report = render_alert_report(packet, decision, investigation)

    assert "SigNoz primary evidence" in report
    assert "Prometheus corroboration only" in report
    assert "g-center-service" in report
    assert "trace-1" in report

    _, frontmatter_block, body = report.split("---", maxsplit=2)
    frontmatter = yaml.safe_load(frontmatter_block)
    validator = Draft202012Validator(load_report_schema())
    errors = sorted(validator.iter_errors(frontmatter), key=lambda error: error.json_path)

    assert not errors
    headings = [line.removeprefix("## ") for line in body.splitlines() if line.startswith("## ")]
    assert headings == BODY_SECTION_ORDER
