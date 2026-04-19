"""Minimal outcome ingest surface for warning-agent feedback artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.feedback.contracts import IncidentOutcome, OutcomeEvidenceLinks, OutcomeSource
from app.feedback.persistence import PersistedOutcomeArtifact, persist_outcome_record
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug_component(value: str) -> str:
    return _NON_ALNUM.sub("_", value.lower()).strip("_")


def _timestamp_component(rfc3339_ts: str) -> str:
    dt = datetime.fromisoformat(rfc3339_ts.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%Y%m%dt%H%M%Sz")


def build_outcome_id(
    *,
    source: OutcomeSource,
    service: str,
    operation: str | None,
    recorded_at: str,
) -> str:
    parts = [source, _slug_component(service), _slug_component(operation or "service"), _timestamp_component(recorded_at)]
    return "out_" + "_".join(filter(None, parts))


@dataclass(frozen=True)
class OutcomeIngestRequest:
    source: OutcomeSource
    recorded_at: str
    service: str
    operation: str | None
    environment: str
    packet_id: str
    decision_id: str
    known_outcome: str
    final_severity_band: str
    final_recommended_action: str
    resolution_summary: str
    investigation_id: str | None = None
    report_id: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    evidence_links: OutcomeEvidenceLinks | None = None
    outcome_id: str | None = None


@dataclass(frozen=True)
class OutcomeIngestReceipt:
    outcome: IncidentOutcome
    persisted: PersistedOutcomeArtifact


def build_outcome_record(request: OutcomeIngestRequest) -> IncidentOutcome:
    outcome_id = request.outcome_id or build_outcome_id(
        source=request.source,
        service=request.service,
        operation=request.operation,
        recorded_at=request.recorded_at,
    )
    outcome: IncidentOutcome = {
        "schema_version": "incident-outcome.v1",
        "outcome_id": outcome_id,
        "source": request.source,
        "recorded_at": request.recorded_at,
        "service": request.service,
        "operation": request.operation,
        "environment": request.environment,
        "input_refs": {
            "packet_id": request.packet_id,
            "decision_id": request.decision_id,
            "investigation_id": request.investigation_id,
            "report_id": request.report_id,
        },
        "summary": {
            "known_outcome": request.known_outcome,
            "final_severity_band": request.final_severity_band,
            "final_recommended_action": request.final_recommended_action,
            "resolution_summary": request.resolution_summary,
        },
        "notes": list(request.notes),
    }
    if request.evidence_links is not None:
        outcome["evidence_links"] = request.evidence_links
    return outcome


def _build_metadata_store(artifact_store: JSONLArtifactStore) -> MetadataStore:
    return MetadataStore(db_path=artifact_store.root / "metadata.sqlite3")


def ingest_incident_outcome(
    request: OutcomeIngestRequest,
    *,
    artifact_store: JSONLArtifactStore,
    metadata_store: MetadataStore | None = None,
) -> OutcomeIngestReceipt:
    metadata_store = metadata_store or _build_metadata_store(artifact_store)
    outcome = build_outcome_record(request)
    persisted = persist_outcome_record(
        outcome,
        artifact_store=artifact_store,
        metadata_store=metadata_store,
    )
    return OutcomeIngestReceipt(outcome=outcome, persisted=persisted)
