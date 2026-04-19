"""Base contract surface for investigation result artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from app.contracts_common import DATA_DIR, load_json_schema, schema_path

SCHEMA_VERSION: Final = "investigation-result.v1"
SCHEMA_FILE: Final = "investigation-result.v1.json"
SCHEMA_PATH: Final[Path] = schema_path(SCHEMA_FILE)
ARTIFACT_DIR: Final[Path] = DATA_DIR / "investigations"

SeverityBand = Literal["P1", "P2", "P3", "P4"]
RecommendedAction = Literal["observe", "open_ticket", "page_owner", "send_to_human_review"]
InvestigatorTier = Literal[
    "local_primary_investigator",
    "cloud_fallback_investigator",
]
ModelProvider = Literal["local_vllm", "openai", "other"]


class InputRefs(TypedDict, total=False):
    packet_id: str
    decision_id: str
    retrieval_packet_ids: list[str]
    prometheus_query_refs: list[str]
    signoz_query_refs: list[str]
    code_search_refs: list[str]
    upstream_report_id: str | None


class InvestigationSummary(TypedDict):
    investigation_used: bool
    severity_band: SeverityBand
    recommended_action: RecommendedAction
    confidence: float
    reason_codes: list[str]
    suspected_primary_cause: str
    failure_chain_summary: str


class Hypothesis(TypedDict):
    rank: int
    hypothesis: str
    confidence: float
    supporting_reason_codes: list[str]


class AnalysisUpdates(TypedDict):
    severity_band_changed: bool
    recommended_action_changed: bool
    fallback_invocation_was_correct: bool | None
    notes: list[str]


class RoutingHints(TypedDict):
    owner_hint: str | None
    repo_candidates: list[str]
    suspected_code_paths: list[str]
    escalation_target: str | None


class InvestigationEvidenceRefs(TypedDict):
    prometheus_ref_ids: list[str]
    signoz_ref_ids: list[str]
    trace_ids: list[str]
    code_refs: list[str]


class CompressedHandoff(TypedDict, total=False):
    handoff_markdown: str
    handoff_tokens_estimate: int
    carry_reason_codes: list[str]


class InvestigationResult(TypedDict):
    schema_version: str
    investigation_id: str
    packet_id: str
    decision_id: str
    parent_investigation_id: NotRequired[str | None]
    investigator_tier: InvestigatorTier
    model_provider: ModelProvider
    model_name: str
    generated_at: str
    input_refs: InputRefs
    summary: InvestigationSummary
    hypotheses: list[Hypothesis]
    analysis_updates: AnalysisUpdates
    routing: RoutingHints
    evidence_refs: InvestigationEvidenceRefs
    unknowns: list[str]
    compressed_handoff: NotRequired[CompressedHandoff]


def load_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE)
