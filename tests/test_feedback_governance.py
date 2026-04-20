from __future__ import annotations

from pathlib import Path

from app.feedback.governance import feedback_governance_payload, load_feedback_governance_config


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_feedback_governance_config_reads_frozen_policy() -> None:
    config = load_feedback_governance_config(REPO_ROOT / "configs" / "feedback-governance.yaml")

    assert config.cadence.retrieval_refresh == "on_each_landed_outcome"
    assert config.promotion.minimum_landed_outcome_cases == 3
    assert config.promotion.auto_promote is False
    assert config.artifact_paths.compare_summary == "data/benchmarks/local-analyzer-feedback-compare-summary.json"
    assert config.rollback.rollback_to_previous_runtime_artifact is True
    assert feedback_governance_payload(config) == {
        "cadence": {
            "retrieval_refresh": "on_each_landed_outcome",
            "corpus_assembly": "on_compare_review_request",
            "retrain_compare": "on_feedback_batch_review",
            "promotion_review": "explicit_manual_review_only",
        },
        "promotion": {
            "minimum_landed_outcome_cases": 3,
            "auto_promote": False,
            "require_candidate_not_worse": True,
            "require_manual_review_report": True,
        },
        "artifact_paths": {
            "compare_corpus": "data/feedback/feedback-compare-corpus.json",
            "compare_summary": "data/benchmarks/local-analyzer-feedback-compare-summary.json",
            "candidate_artifact": "data/models/local-analyzer-trained-scorer.candidate.json",
            "promotion_decision": "data/decisions/local-analyzer-promotion-decision.json",
            "promotion_report": "data/reports/local-analyzer-promotion-report.md",
            "runtime_artifact": "data/models/local-analyzer-trained-scorer.v1.json",
            "previous_runtime_artifact": "data/models/local-analyzer-trained-scorer.prev.json",
        },
        "rollback": {
            "enabled": True,
            "trigger_rule": "regression_or_runtime_smoke_failure_after_manual_promotion",
            "rollback_to_previous_runtime_artifact": True,
        },
    }
