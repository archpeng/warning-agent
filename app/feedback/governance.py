"""Governance config for the warning-agent feedback loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CadenceConfig:
    retrieval_refresh: str
    corpus_assembly: str
    retrain_compare: str
    promotion_review: str


@dataclass(frozen=True)
class PromotionGovernance:
    minimum_landed_outcome_cases: int
    auto_promote: bool
    require_candidate_not_worse: bool
    require_manual_review_report: bool


@dataclass(frozen=True)
class ArtifactPathConfig:
    compare_corpus: str
    compare_summary: str
    candidate_artifact: str
    promotion_decision: str
    promotion_report: str
    runtime_artifact: str
    previous_runtime_artifact: str


@dataclass(frozen=True)
class RollbackGovernance:
    enabled: bool
    trigger_rule: str
    rollback_to_previous_runtime_artifact: bool


@dataclass(frozen=True)
class FeedbackGovernanceConfig:
    cadence: CadenceConfig
    promotion: PromotionGovernance
    artifact_paths: ArtifactPathConfig
    rollback: RollbackGovernance



def feedback_governance_payload(config: FeedbackGovernanceConfig) -> dict[str, object]:
    return {
        "cadence": {
            "retrieval_refresh": config.cadence.retrieval_refresh,
            "corpus_assembly": config.cadence.corpus_assembly,
            "retrain_compare": config.cadence.retrain_compare,
            "promotion_review": config.cadence.promotion_review,
        },
        "promotion": {
            "minimum_landed_outcome_cases": config.promotion.minimum_landed_outcome_cases,
            "auto_promote": config.promotion.auto_promote,
            "require_candidate_not_worse": config.promotion.require_candidate_not_worse,
            "require_manual_review_report": config.promotion.require_manual_review_report,
        },
        "artifact_paths": {
            "compare_corpus": config.artifact_paths.compare_corpus,
            "compare_summary": config.artifact_paths.compare_summary,
            "candidate_artifact": config.artifact_paths.candidate_artifact,
            "promotion_decision": config.artifact_paths.promotion_decision,
            "promotion_report": config.artifact_paths.promotion_report,
            "runtime_artifact": config.artifact_paths.runtime_artifact,
            "previous_runtime_artifact": config.artifact_paths.previous_runtime_artifact,
        },
        "rollback": {
            "enabled": config.rollback.enabled,
            "trigger_rule": config.rollback.trigger_rule,
            "rollback_to_previous_runtime_artifact": config.rollback.rollback_to_previous_runtime_artifact,
        },
    }



def load_feedback_governance_config(
    config_path: str | Path = Path("configs/feedback-governance.yaml"),
) -> FeedbackGovernanceConfig:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("feedback governance config must be a mapping")

    feedback_loop = payload["feedback_loop"]
    cadence = feedback_loop["cadence"]
    promotion = feedback_loop["promotion"]
    artifact_paths = feedback_loop["artifact_paths"]
    rollback = feedback_loop["rollback"]

    return FeedbackGovernanceConfig(
        cadence=CadenceConfig(
            retrieval_refresh=str(cadence["retrieval_refresh"]),
            corpus_assembly=str(cadence["corpus_assembly"]),
            retrain_compare=str(cadence["retrain_compare"]),
            promotion_review=str(cadence["promotion_review"]),
        ),
        promotion=PromotionGovernance(
            minimum_landed_outcome_cases=int(promotion["minimum_landed_outcome_cases"]),
            auto_promote=bool(promotion["auto_promote"]),
            require_candidate_not_worse=bool(promotion["require_candidate_not_worse"]),
            require_manual_review_report=bool(promotion["require_manual_review_report"]),
        ),
        artifact_paths=ArtifactPathConfig(
            compare_corpus=str(artifact_paths["compare_corpus"]),
            compare_summary=str(artifact_paths["compare_summary"]),
            candidate_artifact=str(artifact_paths["candidate_artifact"]),
            promotion_decision=str(artifact_paths["promotion_decision"]),
            promotion_report=str(artifact_paths["promotion_report"]),
            runtime_artifact=str(artifact_paths["runtime_artifact"]),
            previous_runtime_artifact=str(artifact_paths["previous_runtime_artifact"]),
        ),
        rollback=RollbackGovernance(
            enabled=bool(rollback["enabled"]),
            trigger_rule=str(rollback["trigger_rule"]),
            rollback_to_previous_runtime_artifact=bool(rollback["rollback_to_previous_runtime_artifact"]),
        ),
    )
