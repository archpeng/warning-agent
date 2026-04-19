"""Outcome-driven retrieval refresh helpers for warning-agent feedback loops."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.feedback.contracts import IncidentOutcome
from app.retrieval.index import RetrievalIndex
from app.storage.artifact_store import JSONLArtifactStore


@dataclass(frozen=True)
class OutcomeRetrievalRefreshResult:
    refreshed_count: int
    retrieval_db_path: str
    refreshed_doc_ids: tuple[str, ...]


def render_outcome_retrieval_body(outcome: IncidentOutcome) -> str:
    summary = outcome["summary"]
    payload = {
        "outcome_id": outcome["outcome_id"],
        "source": outcome["source"],
        "service": outcome["service"],
        "operation": outcome.get("operation"),
        "environment": outcome["environment"],
        "packet_id": outcome["input_refs"]["packet_id"],
        "decision_id": outcome["input_refs"]["decision_id"],
        "investigation_id": outcome["input_refs"]["investigation_id"],
        "report_id": outcome["input_refs"]["report_id"],
        "known_outcome": summary["known_outcome"],
        "final_severity_band": summary["final_severity_band"],
        "final_recommended_action": summary["final_recommended_action"],
        "resolution_summary": summary["resolution_summary"],
        "notes": outcome.get("notes", []),
        "evidence_links": outcome.get("evidence_links", {}),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def refresh_outcome_retrieval_docs(
    *,
    artifact_store: JSONLArtifactStore,
    retrieval_index: RetrievalIndex | None = None,
) -> OutcomeRetrievalRefreshResult:
    retrieval_index = retrieval_index or RetrievalIndex(db_path=artifact_store.root / "retrieval" / "retrieval.sqlite3")
    retrieval_index.initialize()

    refreshed_doc_ids: list[str] = []
    for record in artifact_store.read_all("outcomes"):
        outcome: IncidentOutcome = record  # type: ignore[assignment]
        retrieval_index.upsert_document(
            doc_id=str(outcome["outcome_id"]),
            kind="outcome",
            service=str(outcome["service"]),
            operation=str(outcome.get("operation") or ""),
            body=render_outcome_retrieval_body(outcome),
        )
        refreshed_doc_ids.append(str(outcome["outcome_id"]))

    return OutcomeRetrievalRefreshResult(
        refreshed_count=len(refreshed_doc_ids),
        retrieval_db_path=str(retrieval_index.db_path),
        refreshed_doc_ids=tuple(refreshed_doc_ids),
    )
