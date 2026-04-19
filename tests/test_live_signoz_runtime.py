from __future__ import annotations

from pathlib import Path

from app.live_signoz_smoke import run_live_signoz_alert_smoke
from app.main import build_runtime_entrypoint
from app.runtime_entry import RuntimeEntrypoint, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNOZ_ALERT_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "signoz-alert.prod-hq-bff-service.error.json"


class EmptyPrometheusCollector:
    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        return None


class FakeSignozCollector:
    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        return []

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        return [
            {"traceId": "trace-1", "error_ratio": 0.88},
            {"traceId": "trace-2", "error_ratio": 0.88},
        ]

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return [
            {
                "name": "POST /api/datamesh/v1/charts/data",
                "p95_ms": 1800.0,
                "error_ratio": 0.88,
            }
        ]

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


def test_build_runtime_entrypoint_accepts_signoz_alert_mode() -> None:
    entrypoint = build_runtime_entrypoint(
        ["signoz-alert", "fixtures/replay/signoz-alert.prod-hq-bff-service.error.json"],
        cwd=REPO_ROOT,
    )

    assert entrypoint == RuntimeEntrypoint(
        mode="signoz_alert",
        replay_fixture=SIGNOZ_ALERT_FIXTURE,
        candidate_source="signoz_alert",
        evidence_source="live",
    )


def test_execute_runtime_entrypoint_materializes_signoz_alert_live_path(tmp_path: Path) -> None:
    entrypoint = RuntimeEntrypoint(
        mode="signoz_alert",
        replay_fixture=SIGNOZ_ALERT_FIXTURE,
        candidate_source="signoz_alert",
        evidence_source="live",
    )
    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=JSONLArtifactStore(root=tmp_path),
        prometheus_collector=EmptyPrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert execution.evidence_fixture is None
    assert execution.packet["candidate_source"] == "signoz_alert"
    assert execution.packet["packet_id"].startswith("ipk_prod_hq_bff_service_post_api_datamesh")
    assert execution.decision["severity_band"] != "P4"
    assert execution.investigation is not None
    assert execution.persisted_artifacts is not None
    assert "SigNoz primary evidence" in execution.report
    assert "Prometheus corroboration only" in execution.report


def test_run_live_signoz_alert_smoke_reports_runtime_summary(tmp_path: Path) -> None:
    summary = run_live_signoz_alert_smoke(
        SIGNOZ_ALERT_FIXTURE,
        repo_root=REPO_ROOT,
        artifact_store=JSONLArtifactStore(root=tmp_path),
        prometheus_collector=EmptyPrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert summary["entrypoint"]["mode"] == "signoz_alert"
    assert summary["entrypoint"]["evidence_source"] == "live"
    assert summary["runtime"]["investigation_stage"] == "local_primary"
    assert summary["packet_candidate_source"] == "signoz_alert"
    assert summary["persisted"] is True
    assert summary["evidence_fixture"] is None
