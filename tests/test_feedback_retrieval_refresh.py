from __future__ import annotations

from pathlib import Path

from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.storage.artifact_store import JSONLArtifactStore


def test_refresh_outcome_retrieval_docs_indexes_landed_outcomes(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    ingest_incident_outcome(
        OutcomeIngestRequest(
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
            resolution_summary="operator confirmed a real incident and rolled back the release",
            notes=("rollback resolved the timeout regression",),
        ),
        artifact_store=artifact_store,
    )
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval.sqlite3")

    refreshed = refresh_outcome_retrieval_docs(artifact_store=artifact_store, retrieval_index=retrieval_index)
    hits = search_documents(retrieval_index, "rollback severe", service="checkout")

    assert refreshed.refreshed_count == 1
    assert refreshed.refreshed_doc_ids == ("out_operator_checkout_post_api_pay_20260419t080000z",)
    assert [hit.doc_id for hit in hits] == ["out_operator_checkout_post_api_pay_20260419t080000z"]
    assert hits[0].kind == "outcome"
