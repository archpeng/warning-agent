from __future__ import annotations

from pathlib import Path

from app.feedback.outcome_ingest import OutcomeIngestRequest, build_outcome_id, ingest_incident_outcome
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


def test_build_outcome_id_is_deterministic_for_source_service_operation_and_timestamp() -> None:
    outcome_id = build_outcome_id(
        source="operator",
        service="checkout",
        operation="POST /api/pay",
        recorded_at="2026-04-19T08:00:00Z",
    )

    assert outcome_id == "out_operator_checkout_post_api_pay_20260419t080000z"


def test_ingest_incident_outcome_writes_artifact_and_metadata(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    request = OutcomeIngestRequest(
        source="operator",
        recorded_at="2026-04-19T08:00:00Z",
        service="checkout",
        operation="POST /api/pay",
        environment="prod",
        packet_id="ipk_checkout_post_api_pay_20260418t120008z",
        decision_id="lad_checkout_post_pay_20260418t120010z",
        investigation_id="inv_checkout_post_pay_20260418t120012z",
        report_id="rpt_checkout_post_api_pay_20260418t120008z",
        known_outcome="severe",
        final_severity_band="P1",
        final_recommended_action="page_owner",
        resolution_summary="operator confirmed a real incident and resolved it with a rollback",
        notes=("rollback applied",),
    )

    receipt = ingest_incident_outcome(request, artifact_store=artifact_store)
    metadata_store = MetadataStore(db_path=receipt.persisted.metadata_db_path)

    assert receipt.outcome["outcome_id"] == "out_operator_checkout_post_api_pay_20260419t080000z"
    assert [record["outcome_id"] for record in artifact_store.read_all("outcomes")] == [
        "out_operator_checkout_post_api_pay_20260419t080000z"
    ]
    assert metadata_store.list_artifacts("outcomes") == [
        {
            "artifact_id": "out_operator_checkout_post_api_pay_20260419t080000z",
            "schema_version": "incident-outcome.v1",
            "service": "checkout",
            "operation": "POST /api/pay",
            "created_at": "2026-04-19T08:00:00Z",
            "artifact_path": str(artifact_store.artifact_path("outcomes")),
        }
    ]
