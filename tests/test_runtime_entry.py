from __future__ import annotations

from pathlib import Path

from app.delivery.bridge_result import BridgeDispatchResult
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.main import RuntimeEntrypoint, build_runtime_entrypoint
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.runtime_entry import execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"



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



def test_execute_runtime_entrypoint_materializes_replay_path_without_persistence() -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )

    execution = execute_runtime_entrypoint(entrypoint, repo_root=REPO_ROOT, persist_artifacts=False)

    assert entrypoint == RuntimeEntrypoint(
        mode="replay",
        replay_fixture=REPLAY_FIXTURE,
        candidate_source="manual_replay",
    )
    assert execution.evidence_fixture == REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
    assert execution.packet["packet_id"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert execution.decision["decision_id"] == "lad_checkout_post_pay_20260418t120010z"
    assert execution.decision["analyzer_family"] == "hybrid"
    assert execution.decision["analyzer_version"] == "trained-scorer-2026-04-19"
    assert execution.investigation is not None
    assert execution.investigation["investigator_tier"] == "cloud_fallback_investigator"
    assert execution.report.startswith("---\nschema_version: alert-report.v1")
    assert "investigation_stage: cloud_fallback" in execution.report
    assert "db timeout on order lookup" in execution.report
    assert execution.persisted_artifacts is None


def test_execute_runtime_entrypoint_persists_runtime_artifacts_and_sidecars(tmp_path: Path) -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )
    store = JSONLArtifactStore(root=tmp_path)

    execution = execute_runtime_entrypoint(entrypoint, repo_root=REPO_ROOT, artifact_store=store)

    assert execution.persisted_artifacts is not None
    assert execution.persisted_artifacts.packet_path == tmp_path / "packets" / "packets.jsonl"
    assert execution.persisted_artifacts.decision_path == tmp_path / "decisions" / "decisions.jsonl"
    assert execution.persisted_artifacts.investigation_path == tmp_path / "investigations" / "investigations.jsonl"
    assert execution.persisted_artifacts.report_path == tmp_path / "reports" / "reports.jsonl"
    assert execution.persisted_artifacts.delivery_dispatches_path == tmp_path / "deliveries" / "deliveries.jsonl"
    assert execution.persisted_artifacts.metadata_db_path == tmp_path / "metadata.sqlite3"
    assert execution.persisted_artifacts.retrieval_db_path == tmp_path / "retrieval" / "retrieval.sqlite3"

    packet_records = store.read_all("packets")
    decision_records = store.read_all("decisions")
    investigation_records = store.read_all("investigations")
    report_records = store.read_all("reports")
    delivery_records = store.read_all("deliveries")

    assert [record["packet_id"] for record in packet_records] == ["ipk_checkout_post_api_pay_20260418t120008z"]
    assert [record["decision_id"] for record in decision_records] == ["lad_checkout_post_pay_20260418t120010z"]
    assert [record["analyzer_family"] for record in decision_records] == ["hybrid"]
    assert [record["analyzer_version"] for record in decision_records] == ["trained-scorer-2026-04-19"]
    assert [record["investigator_tier"] for record in investigation_records] == ["cloud_fallback_investigator"]
    assert [record["report_id"] for record in report_records] == ["rpt_checkout_post_api_pay_20260418t120008z"]
    assert report_records[0]["schema_version"] == "alert-report.v1"
    assert report_records[0]["investigation_stage"] == "cloud_fallback"
    assert "## Executive Summary" in report_records[0]["markdown"]
    assert [record["delivery_class"] for record in delivery_records] == ["page_owner"]
    assert [record["route_adapter"] for record in delivery_records] == ["adapter_feishu"]
    assert [record["delivery_mode"] for record in delivery_records] == ["env_gated_live"]
    assert [record["status"] for record in delivery_records] == ["deferred"]
    assert [record["env_gate_state"] for record in delivery_records] == ["missing_env"]
    assert delivery_records[0]["queue"] is None
    assert delivery_records[0]["target_channel"] == "feishu"
    assert delivery_records[0]["target_ref"] is None
    assert delivery_records[0]["live_endpoint"] is None
    assert delivery_records[0]["bridge_payload_path"] is None
    assert Path(delivery_records[0]["payload_path"]).exists()

    metadata_store = MetadataStore(db_path=execution.persisted_artifacts.metadata_db_path)
    assert [record["artifact_id"] for record in metadata_store.list_artifacts("packets")] == [
        "ipk_checkout_post_api_pay_20260418t120008z"
    ]
    assert [record["artifact_id"] for record in metadata_store.list_artifacts("local_decisions")] == [
        "lad_checkout_post_pay_20260418t120010z"
    ]
    assert [record["artifact_id"] for record in metadata_store.list_artifacts("investigations")] == [
        "cir_checkout_post_api_pay_20260418t120024z_cloud"
    ]
    assert [record["artifact_id"] for record in metadata_store.list_artifacts("alert_reports")] == [
        "rpt_checkout_post_api_pay_20260418t120008z"
    ]

    retrieval_index = RetrievalIndex(db_path=execution.persisted_artifacts.retrieval_db_path)
    hits = search_documents(retrieval_index, "timeout", service="checkout")

    assert hits
    assert {hit.doc_id for hit in hits} >= {
        "cir_checkout_post_api_pay_20260418t120024z_cloud",
        "rpt_checkout_post_api_pay_20260418t120008z",
    }
    assert {hit.kind for hit in hits} >= {"investigation", "alert_report"}



def test_execute_runtime_entrypoint_persists_feishu_bridge_payload_when_env_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)
    monkeypatch.setattr(
        "app.delivery.runtime.post_adapter_feishu_notification",
        lambda endpoint, payload, timeout_seconds: BridgeDispatchResult(
            status="delivered",
            response_code=202,
            provider_key="warning-agent",
            provider_status="delivered",
            message=None,
            external_ref="msg-1",
            raw_response={"code": 0, "providerKey": "warning-agent", "status": "delivered"},
        ),
    )
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )
    store = JSONLArtifactStore(root=tmp_path)

    execution = execute_runtime_entrypoint(entrypoint, repo_root=REPO_ROOT, artifact_store=store)

    assert execution.persisted_artifacts is not None
    delivery_records = store.read_all("deliveries")
    assert [record["route_adapter"] for record in delivery_records] == ["adapter_feishu"]
    assert [record["delivery_mode"] for record in delivery_records] == ["env_gated_live"]
    assert [record["status"] for record in delivery_records] == ["delivered"]
    assert [record["env_gate_state"] for record in delivery_records] == ["ready"]
    assert delivery_records[0]["response_code"] == 202
    assert delivery_records[0]["provider_key"] == "warning-agent"
    assert delivery_records[0]["provider_status"] == "delivered"
    assert delivery_records[0]["external_ref"] == "msg-1"
    assert delivery_records[0]["target_ref"] == "oc-test-chat"
    assert delivery_records[0]["live_endpoint"] == "http://127.0.0.1:8787/providers/webhook"
    assert delivery_records[0]["bridge_payload_path"] is not None
    assert Path(delivery_records[0]["bridge_payload_path"]).exists()



def test_execute_runtime_entrypoint_passes_retrieval_hits_into_runtime_scoring(tmp_path: Path) -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )
    store = JSONLArtifactStore(root=tmp_path)
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")
    _seed_checkout_outcome_retrieval(store, retrieval_index)

    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=REPO_ROOT,
        artifact_store=store,
        retrieval_index=retrieval_index,
    )

    assert execution.decision["retrieval_hits"] == [
        {
            "packet_id": "ipk_checkout_reference_20260417t090000z",
            "similarity": 0.9,
            "known_outcome": "severe",
        }
    ]
