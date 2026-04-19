"""Persistence helpers for outcome feedback artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from app.feedback.contracts import IncidentOutcome, load_schema
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


@dataclass(frozen=True)
class PersistedOutcomeArtifact:
    artifact_path: Path
    metadata_db_path: Path


def validate_outcome_record(outcome: IncidentOutcome) -> None:
    validator = Draft202012Validator(load_schema())
    errors = sorted(validator.iter_errors(outcome), key=lambda error: error.json_path)
    if errors:
        joined = "; ".join(f"{error.json_path or '$'}: {error.message}" for error in errors)
        raise ValueError(f"invalid incident outcome artifact: {joined}")


def _build_metadata_store(artifact_store: JSONLArtifactStore) -> MetadataStore:
    return MetadataStore(db_path=artifact_store.root / "metadata.sqlite3")


def persist_outcome_record(
    outcome: IncidentOutcome,
    *,
    artifact_store: JSONLArtifactStore,
    metadata_store: MetadataStore | None = None,
) -> PersistedOutcomeArtifact:
    validate_outcome_record(outcome)

    artifact_path = artifact_store.append("outcomes", outcome)
    metadata_store = metadata_store or _build_metadata_store(artifact_store)
    metadata_store.initialize()
    metadata_store.record_artifact(
        "outcomes",
        artifact_id=str(outcome["outcome_id"]),
        schema_version=str(outcome["schema_version"]),
        artifact_path=str(artifact_path),
        service=str(outcome["service"]),
        operation=str(outcome.get("operation") or ""),
        created_at=str(outcome["recorded_at"]),
    )

    return PersistedOutcomeArtifact(
        artifact_path=artifact_path,
        metadata_db_path=metadata_store.db_path,
    )
