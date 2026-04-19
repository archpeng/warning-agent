from __future__ import annotations

from pathlib import Path

from app.live_runtime_smoke import run_live_runtime_smoke
from app.storage.artifact_store import JSONLArtifactStore


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
        return [{"traceId": "7f8a3c", "error_ratio": 0.34}, {"traceId": "7f8a40", "error_ratio": 0.34}]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return [{"name": "POST /api/pay", "p95_ms": 2400.0, "error_ratio": 0.34}]


def test_run_live_runtime_smoke_reports_live_entrypoint_summary(tmp_path: Path) -> None:
    summary = run_live_runtime_smoke(
        REPLAY_FIXTURE,
        repo_root=REPO_ROOT,
        artifact_store=JSONLArtifactStore(root=tmp_path),
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert summary["entrypoint"]["evidence_source"] == "live"
    assert summary["runtime"]["packet_id"] == "ipk_checkout_post_api_pay_20260419t100000z"
    assert summary["runtime"]["decision_id"] == "lad_checkout_post_pay_20260419t100002z"
    assert summary["packet_service"] == "checkout"
    assert summary["persisted"] is True
    assert summary["evidence_fixture"] is None
