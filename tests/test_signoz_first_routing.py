from __future__ import annotations

from pathlib import Path

from app.analyzer.base import load_thresholds
from app.analyzer.fast_scorer import FastScorer
from app.analyzer.trained_scorer import DEFAULT_TRAINED_SCORER_ARTIFACT_PATH, TrainedScorer
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.signoz_alert import normalize_signoz_alert_payload


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_signoz_primary_packet() -> dict[str, object]:
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
                    "template_id": "log-1",
                    "template": "trace-specific timeout at downstream dependency",
                    "count": 9,
                    "novelty_score": 0.84,
                }
            ],
            "top_slow_operations": [
                {
                    "operation": "POST /api/datamesh/v1/charts/data",
                    "p95_ms": 1850.0,
                    "error_ratio": 0.78,
                }
            ],
            "trace_error_ratio": None,
            "sample_trace_ids": [],
            "sample_log_refs": ["signoz-mcp://log-row/log-1"],
            "alert_context": {
                "rule_id": "019d1fad-feb8-74c3-9610-dd894c6390d0",
                "source_url": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
                "eval_window": "5m0s",
                "severity": "error",
            },
            "trace_detail_hints": [],
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
            "signoz_query_refs": ["signoz-mcp://alert?rule_id=019d1fad-feb8-74c3-9610-dd894c6390d0"],
        },
    }
    return build_incident_packet_from_bundle(normalized, bundle)


def test_fast_scorer_promotes_signoz_alert_and_top_operations_without_prometheus() -> None:
    packet = _build_signoz_primary_packet()
    scorer = FastScorer(load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"))

    decision = scorer.score_packet(packet, retrieval_hits=[])

    assert decision["severity_score"] >= 0.5
    assert decision["severity_band"] != "P4"
    assert decision["needs_investigation"] is True
    assert "signoz_alert_firing" in decision["reason_codes"]


def test_trained_scorer_keeps_signoz_primary_packet_at_or_above_fast_scorer() -> None:
    packet = _build_signoz_primary_packet()
    thresholds = load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml")
    fast_decision = FastScorer(thresholds).score_packet(packet, retrieval_hits=[])
    trained = TrainedScorer.from_artifact_path(
        REPO_ROOT / DEFAULT_TRAINED_SCORER_ARTIFACT_PATH,
        thresholds=thresholds,
    )

    decision = trained.score_packet(packet, retrieval_hits=[])

    assert decision["severity_score"] >= fast_decision["severity_score"]
    assert decision["severity_band"] == fast_decision["severity_band"]
    assert decision["needs_investigation"] is True
    assert "signoz_alert_firing" in decision["reason_codes"]
