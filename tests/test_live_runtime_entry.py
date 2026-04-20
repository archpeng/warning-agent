from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.runtime_entry as runtime_entry_module
from app.analyzer.runtime import resolve_runtime_scorer as resolve_actual_runtime_scorer
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.investigator.local_primary import (
    LocalPrimaryInvestigator,
    prewarm_local_primary_resident_service,
    reset_local_primary_resident_service,
)
from app.investigator.router import load_investigator_routing_config
from app.investigator.runtime import run_investigation_runtime as run_actual_investigation_runtime
from app.investigator.tools import BoundedInvestigatorTools
from app.main import RuntimeEntrypoint, build_runtime_entrypoint
from app.receiver.alertmanager_webhook import WEBHOOK_PATH, build_webhook_receipt, create_app
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.runtime_entry import execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


@pytest.fixture(autouse=True)
def _reset_local_primary_resident_runtime() -> None:
    reset_local_primary_resident_service()
    yield
    reset_local_primary_resident_service()



def _seed_checkout_outcome_retrieval(artifact_store: JSONLArtifactStore, retrieval_index: RetrievalIndex) -> None:
    ingest_incident_outcome(
        OutcomeIngestRequest(
            source="operator",
            recorded_at="2026-04-19T08:00:00Z",
            service="checkout",
            operation="POST /api/pay",
            environment="prod",
            packet_id="ipk_checkout_reference_20260417t090000z",
            decision_id="lad_checkout_reference_20260417t090002z",
            investigation_id="cir_checkout_reference_20260417t090024z_cloud",
            report_id="rpt_checkout_reference_20260417t090000z",
            known_outcome="severe",
            final_severity_band="P1",
            final_recommended_action="page_owner",
            resolution_summary="operator confirmed the checkout timeout incident and rolled back the release",
            notes=("db timeout on order lookup recurred before rollback",),
        ),
        artifact_store=artifact_store,
    )
    refresh_outcome_retrieval_docs(artifact_store=artifact_store, retrieval_index=retrieval_index)



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


def _load_alert_payload() -> dict:
    with REPLAY_FIXTURE.open("r", encoding="utf-8") as handle:
        envelope = json.load(handle)
    return envelope["alert_payload"]


def test_build_runtime_entrypoint_accepts_live_flag() -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "--live", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )

    assert entrypoint == RuntimeEntrypoint(
        mode="replay",
        replay_fixture=REPLAY_FIXTURE,
        candidate_source="manual_replay",
        evidence_source="live",
    )


def test_execute_runtime_entrypoint_materializes_live_replay_path_without_fixture_bundle(tmp_path: Path) -> None:
    entrypoint = RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE, evidence_source="live")
    store = JSONLArtifactStore(root=tmp_path)

    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=store,
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert execution.evidence_fixture is None
    assert execution.packet["packet_id"] == "ipk_checkout_post_api_pay_20260419t100000z"
    assert execution.decision["decision_id"] == "lad_checkout_post_pay_20260419t100002z"
    assert execution.report.startswith("---\nschema_version: alert-report.v1")
    assert execution.persisted_artifacts is not None

    metadata_store = MetadataStore(db_path=tmp_path / "metadata.sqlite3")
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")

    assert [record["artifact_id"] for record in metadata_store.list_artifacts("packets")] == [
        "ipk_checkout_post_api_pay_20260419t100000z"
    ]
    assert {hit.kind for hit in search_documents(retrieval_index, "timeout", service="checkout")} >= {"alert_report"}


def test_webhook_live_mode_returns_runtime_receipt_without_fixture_bundle(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            repo_root=REPO_ROOT,
            data_root=tmp_path,
            evidence_source="live",
            prometheus_collector=FakePrometheusCollector(),
            signoz_collector=FakeSignozCollector(),
            evidence_now="2026-04-19T10:00:00Z",
        )
    )
    response = client.post(WEBHOOK_PATH, json=_load_alert_payload())

    assert response.status_code == 200
    assert response.json() == build_webhook_receipt(
        _load_alert_payload(),
        repo_root=REPO_ROOT,
        data_root=tmp_path,
        evidence_source="live",
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )
    assert response.json()["runtime"]["packet_id"] == "ipk_checkout_post_api_pay_20260419t100000z"



def test_fastapi_startup_prewarms_local_primary_resident_service_once(tmp_path: Path) -> None:
    with TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path)) as client:
        health = client.get("/healthz")
        assert health.status_code == 200

    lifecycle = prewarm_local_primary_resident_service(
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        prewarm_source="provider_init",
    ).lifecycle
    assert lifecycle.prewarm_attempt_count == 1
    assert lifecycle.prewarm_source == "fastapi_startup"
    assert lifecycle.state == "ready"


def test_execute_runtime_entrypoint_live_mode_can_reach_local_primary_investigation(monkeypatch, tmp_path: Path) -> None:
    entrypoint = RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE, evidence_source="live")
    store = JSONLArtifactStore(root=tmp_path)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    local_provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        tools=BoundedInvestigatorTools(
            budget=config.local_primary.budget,
            repo_root=REPO_ROOT,
            signoz_collector=FakeSignozCollector(),
            prometheus_collector=FakePrometheusCollector(),
        ),
    )

    def fake_resolve_runtime_scorer(*, repo_root: Path, thresholds):
        actual = resolve_actual_runtime_scorer(repo_root=repo_root, thresholds=thresholds)

        class _Scorer:
            def score_packet(self, packet: dict[str, object], retrieval_hits: list[object]) -> dict[str, object]:
                decision = actual.score_packet(packet, retrieval_hits=retrieval_hits)
                decision["severity_score"] = 0.96
                decision["confidence"] = 0.9
                decision["needs_investigation"] = True
                return decision

        return _Scorer()

    def fake_run_investigation_runtime(packet, decision, *, config_path, repo_root, runtime_context="direct_runtime"):
        return run_actual_investigation_runtime(
            packet,
            decision,
            config_path=config_path,
            repo_root=repo_root,
            local_provider=local_provider,
            runtime_context=runtime_context,
        )

    monkeypatch.setattr(runtime_entry_module, "resolve_runtime_scorer", fake_resolve_runtime_scorer)
    monkeypatch.setattr(runtime_entry_module, "run_investigation_runtime", fake_run_investigation_runtime)

    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=store,
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert execution.investigation is not None
    assert execution.investigation["investigator_tier"] == "local_primary_investigator"
    assert execution.persisted_artifacts is not None
    assert "live_prometheus_followup_used" in execution.investigation["analysis_updates"]["notes"]
    assert "live_signoz_logs_used" in execution.investigation["analysis_updates"]["notes"]
    assert execution.investigation["summary"]["suspected_primary_cause"] == "db timeout on order lookup"
    assert execution.investigation["evidence_refs"]["trace_ids"][:2] == ["7f8a3c", "7f8a40"]
    assert execution.report.startswith("---\nschema_version: alert-report.v1")



def test_execute_runtime_entrypoint_live_mode_passes_retrieval_hits_into_runtime_scoring(tmp_path: Path) -> None:
    entrypoint = RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE, evidence_source="live")
    store = JSONLArtifactStore(root=tmp_path)
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")
    _seed_checkout_outcome_retrieval(store, retrieval_index)

    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=store,
        retrieval_index=retrieval_index,
        prometheus_collector=FakePrometheusCollector(),
        signoz_collector=FakeSignozCollector(),
        evidence_now="2026-04-19T10:00:00Z",
    )

    assert execution.decision["retrieval_hits"] == [
        {
            "packet_id": "ipk_checkout_reference_20260417t090000z",
            "similarity": 0.9,
            "known_outcome": "severe",
        }
    ]



def test_execute_runtime_entrypoint_prewarms_local_primary_resident_service_once(tmp_path: Path) -> None:
    entrypoint = RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE, evidence_source="fixture")
    store = JSONLArtifactStore(root=tmp_path)

    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=store,
    )

    lifecycle = prewarm_local_primary_resident_service(
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        prewarm_source="provider_init",
    ).lifecycle

    assert execution.packet["packet_id"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert lifecycle.prewarm_attempt_count == 1
    assert lifecycle.prewarm_source == "runtime_entry_boot"
    assert lifecycle.state == "ready"
    assert lifecycle.provider_mode == "smoke_resident"
