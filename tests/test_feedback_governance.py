from __future__ import annotations

from pathlib import Path

from app.feedback.governance import load_feedback_governance_config


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_feedback_governance_config_reads_frozen_policy() -> None:
    config = load_feedback_governance_config(REPO_ROOT / "configs" / "feedback-governance.yaml")

    assert config.cadence.retrieval_refresh == "on_each_landed_outcome"
    assert config.promotion.minimum_landed_outcome_cases == 3
    assert config.promotion.auto_promote is False
    assert config.artifact_paths.compare_summary == "data/benchmarks/local-analyzer-feedback-compare-summary.json"
    assert config.rollback.rollback_to_previous_runtime_artifact is True
