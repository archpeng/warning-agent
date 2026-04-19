from __future__ import annotations

from pathlib import Path

from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents, search_labeled_outcomes
from app.storage.artifact_store import JSONLArtifactStore


def test_retrieval_index_search_returns_expected_hits(tmp_path: Path) -> None:
    index = RetrievalIndex(db_path=tmp_path / "retrieval.sqlite3")
    index.initialize()
    index.upsert_document(
        doc_id="ipk_checkout_1",
        kind="packet",
        service="checkout",
        operation="POST /api/pay",
        body="checkout payment timeout retry burst",
    )
    index.upsert_document(
        doc_id="ipk_orders_1",
        kind="packet",
        service="orders",
        operation="POST /api/create",
        body="orders create success steady state",
    )

    hits = search_documents(index, "checkout timeout", service="checkout")

    assert [hit.doc_id for hit in hits] == ["ipk_checkout_1"]
    assert hits[0].service == "checkout"



def test_search_labeled_outcomes_returns_runtime_ready_hits(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval.sqlite3")
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

    hits = search_labeled_outcomes(retrieval_index, "timeout OR order OR lookup", service="checkout")

    assert hits == [
        {
            "packet_id": "ipk_checkout_reference_20260417t090000z",
            "similarity": 0.9,
            "known_outcome": "severe",
        }
    ]
