"""Search helpers over the warning-agent retrieval index."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.analyzer.contracts import RetrievalHit as AnalyzerRetrievalHit
from app.retrieval.index import RetrievalIndex


@dataclass(frozen=True)
class RetrievalHit:
    doc_id: str
    kind: str
    service: str
    operation: str
    score: float


@dataclass(frozen=True)
class RetrievalDocument:
    doc_id: str
    kind: str
    service: str
    operation: str
    score: float
    body: str


_VALID_KNOWN_OUTCOMES = {"severe", "benign", "unknown"}


def search_documents(
    index: RetrievalIndex,
    query: str,
    *,
    service: str | None = None,
    limit: int = 5,
) -> list[RetrievalHit]:
    return [RetrievalHit(**row) for row in index.search(query, service=service, limit=limit)]



def search_documents_with_body(
    index: RetrievalIndex,
    query: str,
    *,
    service: str | None = None,
    limit: int = 5,
) -> list[RetrievalDocument]:
    return [
        RetrievalDocument(**row)
        for row in index.search(query, service=service, limit=limit, include_body=True)
    ]



def _rank_similarity(rank: int) -> float:
    return round(max(0.1, 1.0 - (rank * 0.1)), 2)



def search_labeled_outcomes(
    index: RetrievalIndex,
    query: str,
    *,
    service: str | None = None,
    limit: int = 5,
) -> list[AnalyzerRetrievalHit]:
    labeled_hits: list[AnalyzerRetrievalHit] = []
    seen_packet_ids: set[str] = set()

    for document in search_documents_with_body(index, query, service=service, limit=limit * 4):
        if document.kind != "outcome":
            continue
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            continue

        packet_id = payload.get("packet_id")
        known_outcome = payload.get("known_outcome")
        if not isinstance(packet_id, str) or known_outcome not in _VALID_KNOWN_OUTCOMES:
            continue
        if packet_id in seen_packet_ids:
            continue

        seen_packet_ids.add(packet_id)
        labeled_hits.append(
            {
                "packet_id": packet_id,
                "similarity": _rank_similarity(len(labeled_hits) + 1),
                "known_outcome": known_outcome,
            }
        )
        if len(labeled_hits) >= limit:
            break

    return labeled_hits
