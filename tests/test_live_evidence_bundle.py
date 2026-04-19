from __future__ import annotations

from pathlib import Path

from app.collectors.evidence_bundle import build_live_evidence_bundle, load_evidence_collection_config
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


class FakePrometheusCollector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        self.calls.append((query, endpoint_name))
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
    def __init__(self) -> None:
        self.log_calls: list[tuple[str, str, str, int]] = []
        self.trace_calls: list[tuple[str, str, str, int]] = []
        self.operation_calls: list[tuple[str, str]] = []

    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        self.log_calls.append((service, time_range, severity, limit))
        return [
            {"id": "log-1", "body": "db timeout on order lookup", "count": 182, "novelty_score": 0.91},
        ]

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        self.trace_calls.append((service, time_range, error, limit))
        return [
            {"traceId": "7f8a3c", "error_ratio": 0.34},
            {"traceId": "7f8a40", "error_ratio": 0.34},
        ]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        self.operation_calls.append((service, time_range))
        return [
            {"name": "POST /api/pay", "p95_ms": 2400.0, "error_ratio": 0.34},
        ]


class CrashingPrometheusCollector:
    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        raise RuntimeError("prometheus unavailable")


class CrashingSignozCollector:
    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        raise RuntimeError("signoz logs unavailable")

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        raise RuntimeError("signoz traces unavailable")

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        raise RuntimeError("signoz operations unavailable")


def test_load_evidence_collection_config_reads_defaults_and_service_override() -> None:
    config = load_evidence_collection_config(REPO_ROOT / "configs" / "evidence.yaml")

    assert config.defaults.window_sec == 300
    assert config.defaults.prometheus_endpoint == "primary"
    assert config.defaults.signoz_time_range == "30m"
    assert config.defaults.signoz_trace_details_limit == 2
    assert config.defaults.signoz_trace_logs_limit == 3
    assert "checkout" in config.services
    assert config.services["checkout"].prometheus_queries["error_rate"] == "checkout_error_rate"


def test_build_live_evidence_bundle_assembles_packet_compatible_shape_from_fake_collectors() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")

    bundle = build_live_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        now="2026-04-19T10:00:00Z",
    )

    assert bundle["created_at"] == "2026-04-19T10:00:00Z"
    assert bundle["window"]["duration_sec"] == 300
    assert bundle["prometheus"]["error_rate"] == 0.21
    assert bundle["prometheus"]["latency_p95_delta"] == 1990.0
    assert bundle["prometheus"]["alerts_firing"] == ["high_error_rate"]
    assert bundle["signoz"]["top_error_templates"][0]["template"] == "db timeout on order lookup"
    assert bundle["signoz"]["trace_error_ratio"] == 0.34
    assert bundle["signoz"]["sample_trace_ids"] == ["7f8a3c", "7f8a40"]
    assert bundle["topology"]["owner"] == "payments-oncall"
    assert bundle["topology"]["repo_candidates"] == ["checkout-service", "payment-gateway-client"]
    assert bundle["evidence_refs"]["prometheus_query_refs"][0].startswith("promql://error_rate?")
    assert bundle["evidence_refs"]["signoz_query_refs"][0].startswith("signoz-mcp://logs?")


def test_build_live_evidence_bundle_falls_back_when_collectors_fail() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")

    bundle = build_live_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=CrashingPrometheusCollector(),
        signoz_collector=CrashingSignozCollector(),
        now="2026-04-19T10:00:00Z",
    )

    assert bundle["created_at"] == "2026-04-19T10:00:00Z"
    assert bundle["prometheus"]["error_rate"] is None
    assert bundle["prometheus"]["latency_p95_ms"] is None
    assert bundle["signoz"]["top_error_templates"] == [
        {
            "template_id": "live_fallback_template",
            "template": "checkout POST /api/pay error rate is above threshold",
            "count": 1,
            "novelty_score": 0.5,
        }
    ]
    assert bundle["signoz"]["top_slow_operations"] == [
        {
            "operation": "POST /api/pay",
            "p95_ms": 0.0,
            "error_ratio": None,
        }
    ]
    assert bundle["signoz"]["trace_error_ratio"] is None
    assert bundle["signoz"]["sample_trace_ids"] == []
    assert bundle["signoz"]["sample_log_refs"] == []
    assert len(bundle["evidence_refs"]["prometheus_query_refs"]) >= 1
    assert len(bundle["evidence_refs"]["signoz_query_refs"]) == 3


class RawSignozCollector:
    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        return []

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        return [
            {"traceID": "trace-1"},
            {"trace_id": "trace-1"},
            {"traceID": "trace-2"},
        ]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return [{"name": "POST", "p95": 125000000.0, "errorRate": 0.2}]


def test_build_live_evidence_bundle_normalizes_raw_signoz_shapes() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    normalized["service"] = "prod-hq-bff-service"
    normalized["operation"] = "POST"

    bundle = build_live_evidence_bundle(
        normalized,
        repo_root=REPO_ROOT,
        prometheus_collector=CrashingPrometheusCollector(),
        signoz_collector=RawSignozCollector(),
        now="2026-04-19T10:00:00Z",
    )

    assert bundle["signoz"]["top_slow_operations"] == [
        {"operation": "POST", "p95_ms": 125.0, "error_ratio": 0.2}
    ]
    assert bundle["signoz"]["trace_error_ratio"] == 1.0
    assert bundle["signoz"]["sample_trace_ids"] == ["trace-1", "trace-2"]
