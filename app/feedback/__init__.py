"""Feedback contracts and persistence helpers for warning-agent."""

from app.feedback.compare import (
    DEFAULT_CANDIDATE_ARTIFACT_PATH,
    DEFAULT_COMPARE_SUMMARY_PATH,
    COMPARE_SUMMARY_VERSION,
    run_feedback_retrain_compare,
)
from app.feedback.contracts import IncidentOutcome, SCHEMA_VERSION
from app.feedback.corpus import (
    DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH,
    FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION,
    assemble_feedback_compare_corpus,
)
from app.feedback.outcome_ingest import (
    OutcomeIngestReceipt,
    OutcomeIngestRequest,
    build_outcome_id,
    build_outcome_record,
    ingest_incident_outcome,
)
from app.feedback.persistence import PersistedOutcomeArtifact, persist_outcome_record, validate_outcome_record
from app.feedback.promotion import (
    DEFAULT_PROMOTION_DECISION_PATH,
    DEFAULT_PROMOTION_REPORT_PATH,
    run_feedback_promotion_review,
)
from app.feedback.retrieval_refresh import (
    OutcomeRetrievalRefreshResult,
    refresh_outcome_retrieval_docs,
    render_outcome_retrieval_body,
)

__all__ = [
    "COMPARE_SUMMARY_VERSION",
    "DEFAULT_CANDIDATE_ARTIFACT_PATH",
    "DEFAULT_COMPARE_SUMMARY_PATH",
    "DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH",
    "DEFAULT_PROMOTION_DECISION_PATH",
    "DEFAULT_PROMOTION_REPORT_PATH",
    "FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION",
    "IncidentOutcome",
    "OutcomeIngestReceipt",
    "OutcomeIngestRequest",
    "OutcomeRetrievalRefreshResult",
    "PersistedOutcomeArtifact",
    "SCHEMA_VERSION",
    "assemble_feedback_compare_corpus",
    "build_outcome_id",
    "build_outcome_record",
    "ingest_incident_outcome",
    "run_feedback_retrain_compare",
    "persist_outcome_record",
    "refresh_outcome_retrieval_docs",
    "run_feedback_promotion_review",
    "render_outcome_retrieval_body",
    "validate_outcome_record",
]
