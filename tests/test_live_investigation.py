from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from app.analyzer.base import load_thresholds
from app.analyzer.runtime import resolve_runtime_scorer
from app.collectors.evidence_bundle import build_live_evidence_bundle, build_signoz_first_evidence_bundle
from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.local_primary import LocalPrimaryInvestigator
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.investigator.tools import BoundedInvestigatorTools
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.signoz_alert import normalize_signoz_alert_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


class FakePrometheusCollector:
    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        values = {
            "checkout_error_rate": 0.21,
            "checkout_error_rate_baseline": 0.02,
            "checkout_latency_p95_ms": 2400.0,
            "checkout_latency_p95_baseline_ms": 410.0,
            "checkout_qps": 122.0,
            "checkout_qps_baseline": 118.0,
            "checkout_saturation": 0.81,
        }
        return values[query]


class FakeSignozCollector:
    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        return [{"id": "log-1", "body": "db timeout on order lookup", "count": 182, "novelty_score": 0.91}]

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        return [
            {"traceId": "7f8a3c", "error_ratio": 0.34},
            {"traceId": "7f8a40", "error_ratio": 0.34},
        ]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return [{"name": "POST /api/pay", "p95_ms": 2400.0, "error_ratio": 0.34}]

    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict:
        return {
            "traceId": trace_id,
            "spans": [
                {
                    "name": "grpc.center.CenterService/DeviceInfo",
                    "serviceName": "g-center-service",
                    "server.address": "g-center-service",
                    "responseStatusCode": "503",
                }
            ],
        }

    def search_logs_by_trace_id(self, trace_id: str, *, time_range: str = "30m", limit: int = 5) -> list[dict]:
        return [
            {
                "id": f"trace-log-{trace_id}",
                "body": "downstream dependency 503 timeout",
                "count": 4,
                "novelty_score": 0.82,
            }
        ]


def test_local_primary_uses_live_followup_only_for_live_packet_refs() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    bundle = build_live_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        now="2026-04-19T10:00:00Z",
    )
    packet = build_incident_packet_from_bundle(normalized, bundle)
    decision = resolve_runtime_scorer(
        repo_root=REPO_ROOT,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    ).score_packet(packet, retrieval_hits=[])
    decision["severity_score"] = 0.96
    decision["needs_investigation"] = True
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)
    assert plan.should_investigate is True

    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        tools=BoundedInvestigatorTools(
            budget=config.local_primary.budget,
            repo_root=REPO_ROOT,
            signoz_collector=FakeSignozCollector(),
            prometheus_collector=FakePrometheusCollector(),
        ),
    )
    result = provider.investigate(plan.request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert "live_prometheus_followup_used" in result["analysis_updates"]["notes"]
    assert "live_signoz_logs_used" in result["analysis_updates"]["notes"]
    assert "live_signoz_traces_used" in result["analysis_updates"]["notes"]
    assert any(note.startswith("live_error_rate=") for note in result["analysis_updates"]["notes"])
    assert "bounded live follow-up used Prometheus + SigNoz + repo search; deeper confirmation may still be needed" in result["unknowns"]
    assert result["summary"]["suspected_primary_cause"] == "db timeout on order lookup"
    assert {"7f8a3c", "7f8a40"}.issubset(set(result["evidence_refs"]["trace_ids"]))


def test_local_primary_prefers_signoz_trace_details_for_signoz_first_packets() -> None:
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
    bundle = build_signoz_first_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=None,
        signoz_collector=FakeSignozCollector(),
        now="2026-04-19T10:00:00Z",
    )
    packet = build_incident_packet_from_bundle(normalized, bundle)
    decision = resolve_runtime_scorer(
        repo_root=REPO_ROOT,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    ).score_packet(packet, retrieval_hits=[])
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)

    assert plan.should_investigate is True

    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        tools=BoundedInvestigatorTools(
            budget=config.local_primary.budget,
            repo_root=REPO_ROOT,
            signoz_collector=FakeSignozCollector(),
            prometheus_collector=FakePrometheusCollector(),
        ),
    )
    result = provider.investigate(plan.request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert "packet_signoz_alert_context_used" in result["analysis_updates"]["notes"]
    assert "live_signoz_trace_details_used" in result["analysis_updates"]["notes"]
    assert "live_signoz_trace_logs_used" in result["analysis_updates"]["notes"]
    assert result["summary"]["suspected_primary_cause"] == "downstream dependency 503 timeout"
    assert "g-center-service" in result["summary"]["failure_chain_summary"]
    assert any("g-center-service" in hypothesis["hypothesis"] for hypothesis in result["hypotheses"])
    assert result["evidence_refs"]["trace_ids"]
