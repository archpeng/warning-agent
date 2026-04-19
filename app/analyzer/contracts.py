"""Base contract surface for local analyzer decision artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, TypedDict

from app.contracts_common import DATA_DIR, load_json_schema, schema_path

SCHEMA_VERSION: Final = "local-analyzer-decision.v1"
SCHEMA_FILE: Final = "local-analyzer-decision.v1.json"
SCHEMA_PATH: Final[Path] = schema_path(SCHEMA_FILE)
ARTIFACT_DIR: Final[Path] = DATA_DIR / "decisions"

AnalyzerFamily = Literal["fast_scorer", "small_model", "hybrid"]
SeverityBand = Literal["P1", "P2", "P3", "P4"]
RecommendedAction = Literal["observe", "open_ticket", "page_owner", "send_to_human_review"]
RiskFlag = Literal[
    "rule_miss",
    "high_blast_radius",
    "new_template",
    "owner_unknown",
    "recent_deploy",
    "service_hotspot",
]
KnownOutcome = Literal["severe", "benign", "unknown"]


class RetrievalHit(TypedDict):
    packet_id: str
    similarity: float
    known_outcome: KnownOutcome


class LocalAnalyzerDecision(TypedDict):
    schema_version: str
    decision_id: str
    packet_id: str
    analyzer_family: AnalyzerFamily
    analyzer_version: str
    severity_band: SeverityBand
    severity_score: float
    novelty_score: float
    confidence: float
    needs_investigation: bool
    recommended_action: RecommendedAction
    reason_codes: list[str]
    risk_flags: list[RiskFlag]
    retrieval_hits: list[RetrievalHit]
    investigation_trigger_reasons: list[str]


def load_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE)
