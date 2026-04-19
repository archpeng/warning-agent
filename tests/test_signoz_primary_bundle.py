from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from app.collectors.evidence_bundle import build_prometheus_corroboration, build_signoz_first_evidence_bundle
from app.packet.builder import build_incident_packet_from_bundle
from app.packet.contracts import load_schema as load_packet_schema
from app.receiver.signoz_alert import normalize_signoz_alert_payload


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeSignozPrimaryCollector:
    def __init__(self) -> None:
        self.trace_detail_calls: list[tuple[str, str]] = []
        self.trace_log_calls: list[tuple[str, str, int]] = []

    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        return []

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        return [
            {"traceId": "trace-1", "error_ratio": 0.75},
            {"trace_id": "trace-1", "error_ratio": 0.75},
            {"traceID": "trace-2", "error_ratio": 0.25},
        ]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return [
            {
                "name": "POST /api/datamesh/v1/charts/data",
                "p95_ms": 1825.0,
                "error_ratio": 0.75,
            }
        ]

    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict:
        self.trace_detail_calls.append((trace_id, time_range))
        if trace_id == "trace-1":
            return {
                "traceId": "trace-1",
                "spans": [
                    {
                        "name": "POST /api/datamesh/v1/charts/data",
                        "serviceName": "prod-hq-bff-service",
                        "responseStatusCode": "500",
                    },
                    {
                        "name": "grpc.center.CenterService/DeviceInfo",
                        "serviceName": "g-center-service",
                        "server.address": "g-center-service",
                        "responseStatusCode": "503",
                    },
                ],
            }
        return {
            "traceID": "trace-2",
            "data": {
                "spans": [
                    {
                        "name": "POST downstream checkout",
                        "service.name": "prod-n-rms-pay-service",
                        "network.peer.address": "10.0.0.12",
                        "responseStatusCode": "504",
                    }
                ]
            },
        }

    def search_logs_by_trace_id(self, trace_id: str, *, time_range: str = "30m", limit: int = 5) -> list[dict]:
        self.trace_log_calls.append((trace_id, time_range, limit))
        if trace_id == "trace-1":
            return [
                {
                    "id": "log-trace-1",
                    "body": "trace-specific timeout at downstream dependency",
                    "count": 9,
                    "novelty_score": 0.84,
                }
            ]
        return []


def _normalized_signoz_alert() -> dict[str, object]:
    return normalize_signoz_alert_payload(
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


def test_build_prometheus_corroboration_tolerates_missing_collector() -> None:
    corroboration = build_prometheus_corroboration(
        _normalized_signoz_alert(),
        repo_root=REPO_ROOT,
        prometheus_collector=None,
    )

    assert corroboration == {
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
    }


def test_build_signoz_first_evidence_bundle_is_packet_compatible_without_prometheus() -> None:
    normalized = _normalized_signoz_alert()
    bundle = build_signoz_first_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=None,
        signoz_collector=FakeSignozPrimaryCollector(),
        now="2026-04-19T10:00:00Z",
    )
    packet = build_incident_packet_from_bundle(normalized, bundle)

    validator = Draft202012Validator(load_packet_schema())
    errors = sorted(validator.iter_errors(packet), key=lambda error: error.json_path)

    assert not errors
    assert bundle["prometheus"]["alerts_firing"] == []
    assert bundle["prometheus"]["error_rate"] is None
    assert bundle["signoz"]["top_error_templates"][0]["template"] == "trace-specific timeout at downstream dependency"
    assert bundle["signoz"]["trace_error_ratio"] == 0.58
    assert bundle["signoz"]["sample_trace_ids"] == ["trace-1", "trace-2"]
    assert bundle["signoz"]["alert_context"] == {
        "rule_id": "019d1fad-feb8-74c3-9610-dd894c6390d0",
        "source_url": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
        "eval_window": "5m0s",
        "severity": "error",
    }
    assert bundle["signoz"]["trace_detail_hints"] == [
        {
            "trace_id": "trace-1",
            "span_name": "POST /api/datamesh/v1/charts/data",
            "service_name": "prod-hq-bff-service",
            "target": None,
            "status_code": "500",
        },
        {
            "trace_id": "trace-1",
            "span_name": "grpc.center.CenterService/DeviceInfo",
            "service_name": "g-center-service",
            "target": "g-center-service",
            "status_code": "503",
        },
        {
            "trace_id": "trace-2",
            "span_name": "POST downstream checkout",
            "service_name": "prod-n-rms-pay-service",
            "target": "10.0.0.12",
            "status_code": "504",
        },
    ]
    assert any(ref.startswith("signoz-mcp://alert?") for ref in bundle["evidence_refs"]["signoz_query_refs"])
    assert any(
        ref.startswith("signoz-mcp://trace_detail?trace_id=trace-1")
        for ref in bundle["evidence_refs"]["signoz_query_refs"]
    )
    assert any(
        ref.startswith("signoz-mcp://logs_by_trace?trace_id=trace-1")
        for ref in bundle["evidence_refs"]["signoz_query_refs"]
    )


class RawTraceDetailCollector(FakeSignozPrimaryCollector):
    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict:
        return {
            "status": "success",
            "data": {
                "type": "raw",
                "data": {
                    "results": [
                        {
                            "queryName": "A",
                            "rows": [
                                {
                                    "data": {
                                        "traceID": trace_id,
                                        "name": "GET",
                                        "service.name": "prod-hq-bff-service",
                                        "server.address": "p-datamesh",
                                        "responseStatusCode": "504",
                                    }
                                }
                            ],
                        }
                    ]
                },
            },
        }


def test_build_signoz_first_evidence_bundle_parses_raw_trace_detail_payloads() -> None:
    bundle = build_signoz_first_evidence_bundle(
        _normalized_signoz_alert(),
        repo_root=REPO_ROOT,
        prometheus_collector=None,
        signoz_collector=RawTraceDetailCollector(),
        now="2026-04-19T10:00:00Z",
    )

    assert bundle["signoz"]["trace_detail_hints"] == [
        {
            "trace_id": "trace-1",
            "span_name": "GET",
            "service_name": "prod-hq-bff-service",
            "target": "p-datamesh",
            "status_code": "504",
        },
        {
            "trace_id": "trace-2",
            "span_name": "GET",
            "service_name": "prod-hq-bff-service",
            "target": "p-datamesh",
            "status_code": "504",
        },
    ]
