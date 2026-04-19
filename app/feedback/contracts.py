"""Base contract surface for outcome feedback artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from app.analyzer.contracts import KnownOutcome, RecommendedAction, SeverityBand
from app.contracts_common import DATA_DIR, load_json_schema, schema_path

SCHEMA_VERSION: Final = "incident-outcome.v1"
SCHEMA_FILE: Final = "incident-outcome.v1.json"
SCHEMA_PATH: Final[Path] = schema_path(SCHEMA_FILE)
ARTIFACT_DIR: Final[Path] = DATA_DIR / "outcomes"

OutcomeSource = Literal["operator", "replay_label", "postmortem"]


class OutcomeInputRefs(TypedDict):
    packet_id: str
    decision_id: str
    investigation_id: str | None
    report_id: str | None


class OutcomeSummary(TypedDict):
    known_outcome: KnownOutcome
    final_severity_band: SeverityBand
    final_recommended_action: RecommendedAction
    resolution_summary: str


class OutcomeEvidenceLinks(TypedDict, total=False):
    ticket_id: str
    postmortem_id: str
    replay_case_id: str


class IncidentOutcome(TypedDict):
    schema_version: str
    outcome_id: str
    source: OutcomeSource
    recorded_at: str
    service: str
    operation: str | None
    environment: str
    input_refs: OutcomeInputRefs
    summary: OutcomeSummary
    notes: list[str]
    evidence_links: NotRequired[OutcomeEvidenceLinks]


def load_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE)
