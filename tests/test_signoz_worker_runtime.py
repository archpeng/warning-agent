from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.receiver.signoz_ingress import SIGNOZ_CALLER_HEADER, SIGNOZ_INGRESS_PATH, SIGNOZ_SHARED_TOKEN_ENV
from app.receiver.signoz_worker import classify_signoz_evidence_state, run_signoz_worker_once
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.signoz_warning_store import SignozWarningStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNOZ_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "signoz-alert.prod-hq-bff-service.error.json"


@pytest.fixture(autouse=True)
def _reset_local_primary_resident_runtime() -> None:
    from app.investigator.local_primary import reset_local_primary_resident_service

    reset_local_primary_resident_service()
    yield
    reset_local_primary_resident_service()


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


class EmptySignozCollector:
    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        return []

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        return []

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        return []

    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict:
        return {"traceId": trace_id, "spans": []}

    def search_logs_by_trace_id(self, trace_id: str, *, time_range: str = "30m", limit: int = 5) -> list[dict]:
        return []



def _load_signoz_payload() -> dict[str, object]:
    return json.loads(SIGNOZ_FIXTURE.read_text(encoding="utf-8"))



def _headers() -> dict[str, str]:
    return {
        SIGNOZ_CALLER_HEADER: "signoz-prod",
        "Authorization": "Bearer secret-token",
    }



def _admit_warning(tmp_path: Path, monkeypatch) -> str:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    response = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())
    assert response.status_code == 202
    return response.json()["warning_id"]



def test_signoz_worker_retries_then_completes_after_transient_failure(tmp_path: Path, monkeypatch) -> None:
    warning_id = _admit_warning(tmp_path, monkeypatch)
    store = SignozWarningStore(root=tmp_path)
    attempts = {"count": 0}

    def flaky_processor(current_warning_id: str) -> dict[str, object]:
        assert current_warning_id == warning_id
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient worker failure")
        return {
            "packet_id": "ipk_test_warning",
            "decision_id": "lad_test_warning",
            "report_id": "rpt_test_warning",
            "investigation_stage": "local_primary",
            "delivery_status": "deferred",
            "evidence_state": "partial",
            "human_review_required": True,
            "recommended_action": "send_to_human_review",
            "runtime_artifacts": {
                "packet_path": str(tmp_path / "packets.json"),
                "decision_path": str(tmp_path / "decisions.json"),
                "investigation_path": None,
                "report_path": str(tmp_path / "reports.md"),
                "delivery_dispatches_path": None,
                "metadata_db_path": None,
                "retrieval_db_path": None,
                "rollout_evidence_path": None,
            },
        }

    first = run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:00Z",
        retry_backoff_sec=30,
        processor=flaky_processor,
    )
    assert first is not None
    assert first["queue"]["queue_state"] == "failed"
    assert first["queue"]["attempt_count"] == 1
    assert first["queue"]["last_error"] == {
        "code": "worker_execution_failed",
        "message": "transient worker failure",
    }

    before_retry = run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:20Z",
        retry_backoff_sec=30,
        processor=flaky_processor,
    )
    assert before_retry is None

    second = run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:31Z",
        retry_backoff_sec=30,
        processor=flaky_processor,
    )
    assert second is not None
    assert second["queue"]["queue_state"] == "completed"
    assert second["processing_result"]["human_review_required"] is True
    assert second["processing_result"]["recommended_action"] == "send_to_human_review"
    assert store.get_warning_row(warning_id)["attempt_count"] == 2



def test_signoz_worker_moves_poison_warning_to_dead_letter_after_max_attempts(tmp_path: Path, monkeypatch) -> None:
    warning_id = _admit_warning(tmp_path, monkeypatch)
    store = SignozWarningStore(root=tmp_path)

    def crashing_processor(current_warning_id: str) -> dict[str, object]:
        assert current_warning_id == warning_id
        raise RuntimeError("poison warning")

    assert run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:00Z",
        retry_backoff_sec=1,
        max_attempts=3,
        processor=crashing_processor,
    )["queue"]["queue_state"] == "failed"
    assert run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:02Z",
        retry_backoff_sec=1,
        max_attempts=3,
        processor=crashing_processor,
    )["queue"]["queue_state"] == "failed"
    third = run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:04Z",
        retry_backoff_sec=1,
        max_attempts=3,
        processor=crashing_processor,
    )
    assert third is not None
    assert third["queue"]["queue_state"] == "dead_letter"
    assert store.get_warning_row(warning_id)["queue_state"] == "dead_letter"



def test_signoz_worker_executes_canonical_runtime_spine_for_admitted_warning(tmp_path: Path, monkeypatch) -> None:
    warning_id = _admit_warning(tmp_path, monkeypatch)
    store = SignozWarningStore(root=tmp_path)
    artifact_store = JSONLArtifactStore(root=tmp_path)

    result = run_signoz_worker_once(
        store=store,
        repo_root=REPO_ROOT,
        now="2026-04-20T13:00:00Z",
        artifact_store=artifact_store,
        prometheus_collector=EmptyPrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-20T13:00:00Z",
    )

    assert result is not None
    assert result["warning_id"] == warning_id
    assert result["queue"]["queue_state"] == "completed"
    assert result["processing_result"]["packet_id"].startswith("ipk_prod_hq_bff_service_post_api_datamesh")
    assert result["processing_result"]["decision_id"].startswith("lad_prod_hq_bff_service")
    assert result["processing_result"]["report_id"].startswith("rpt_prod_hq_bff_service")
    assert result["processing_result"]["delivery_status"] in {"queued", "deferred"}
    assert result["processing_result"]["evidence_state"] == "complete"

    packets = artifact_store.read_all("packets")
    decisions = artifact_store.read_all("decisions")
    reports = artifact_store.read_all("reports")
    assert packets and packets[0]["candidate_source"] == "signoz_alert"
    assert decisions and decisions[0]["decision_id"] == result["processing_result"]["decision_id"]
    assert reports and reports[0]["report_id"] == result["processing_result"]["report_id"]



def test_signoz_worker_requeues_warning_when_local_primary_needs_recovery_wait(tmp_path: Path, monkeypatch) -> None:
    warning_id = _admit_warning(tmp_path, monkeypatch)
    store = SignozWarningStore(root=tmp_path)
    monkeypatch.setenv("WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("WARNING_AGENT_LOCAL_PRIMARY_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("WARNING_AGENT_LOCAL_PRIMARY_MODEL", "gemma4-26b")

    def fail_resident_warmup(*args, **kwargs):
        raise RuntimeError("resident endpoint refused warmup")

    monkeypatch.setattr("app.investigator.local_primary.build_real_local_primary_provider", fail_resident_warmup)

    result = run_signoz_worker_once(
        store=store,
        repo_root=REPO_ROOT,
        now="2026-04-20T13:00:00Z",
        retry_backoff_sec=30,
        artifact_store=JSONLArtifactStore(root=tmp_path),
        prometheus_collector=EmptyPrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-20T13:00:00Z",
    )

    assert result is not None
    assert result["warning_id"] == warning_id
    assert result["queue"]["queue_state"] == "waiting_local_primary_recovery"
    assert result["queue"]["deferred_reason"] == {
        "code": "local_primary_recovery_wait",
        "message": "local_primary resident prewarm failed: resident endpoint refused warmup",
    }
    assert result["recovery_wait"]["resident_lifecycle"]["state"] == "degraded"
    assert result["recovery_wait"]["abnormal_path"]["action"] == "queue_wait_for_local_primary_recovery"
    assert result["recovery_wait"]["abnormal_path"]["runtime_context"] == "warning_worker"
    assert store.get_warning_row(warning_id)["queue_state"] == "waiting_local_primary_recovery"



def test_signoz_worker_records_partial_evidence_state_machine_readably() -> None:
    assert classify_signoz_evidence_state(
        {
            "signoz": {
                "sample_trace_ids": [],
                "sample_log_refs": [],
                "trace_error_ratio": None,
            }
        }
    ) == "partial"
    assert classify_signoz_evidence_state(
        {
            "signoz": {
                "sample_trace_ids": ["trace-1"],
                "sample_log_refs": [],
                "trace_error_ratio": 0.5,
            }
        }
    ) == "complete"



def test_signoz_worker_uses_partial_state_when_runtime_evidence_is_sparse(tmp_path: Path, monkeypatch) -> None:
    _admit_warning(tmp_path, monkeypatch)
    store = SignozWarningStore(root=tmp_path)

    result = run_signoz_worker_once(
        store=store,
        repo_root=REPO_ROOT,
        now="2026-04-20T13:00:00Z",
        artifact_store=JSONLArtifactStore(root=tmp_path),
        prometheus_collector=EmptyPrometheusCollector(),
        signoz_collector=EmptySignozCollector(),
        evidence_now="2026-04-20T13:00:00Z",
    )

    assert result is not None
    assert result["processing_result"]["evidence_state"] == "partial"
    assert result["processing_result"]["delivery_status"] in {"queued", "deferred"}
