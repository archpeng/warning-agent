from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.training_scaffold import run_trained_scorer_scaffold


REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"
TEMPORAL_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json"


def test_trained_scorer_scaffold_writes_truthful_blocked_summary_and_artifact_preview(tmp_path: Path) -> None:
    summary_path = tmp_path / "local-analyzer-training-scaffold-summary.json"
    artifact_path = tmp_path / "local-analyzer-trained-scorer.scaffold.json"

    summary = run_trained_scorer_scaffold(
        calibration_corpus_path=CALIBRATION_CORPUS,
        temporal_corpus_path=TEMPORAL_CORPUS,
        summary_output_path=summary_path,
        artifact_output_path=artifact_path,
        repo_root=REPO_ROOT,
    )

    written_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    written_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert summary == written_summary
    assert summary["summary_version"] == "local-analyzer-training-scaffold-summary.v1"
    assert summary["feature_set_version"] == "temporal-context-v2.features.v1"
    assert summary["base_analyzer_version"] == "fast-scorer-2026-04-19"
    assert summary["candidate_model_family"] == "logistic_regression"
    assert summary["candidate_calibration_method"] == "platt_scaling"
    assert summary["corpus_contract"]["accepted_labeled_case_count"] == 30
    assert summary["corpus_contract"]["accepted_labeled_severe_case_count"] == 8
    assert summary["corpus_contract"]["temporal_base_case_count"] == 12
    assert summary["corpus_contract"]["training_ready"] is True
    assert summary["corpus_contract"]["blocking_reasons"] == []
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["blockers"] == []

    assert written_artifact["artifact_version"] == "local-analyzer-trained-scorer.scaffold.v1"
    assert written_artifact["model_family"] == "logistic_regression"
    assert written_artifact["calibration_method"] == "platt_scaling"
    assert written_artifact["training_state"] == "ready"
    assert written_artifact["feature_columns"] == [
        "error_rate_regression",
        "latency_regression",
        "qps_shift",
        "anomaly_persistence",
        "deploy_recency",
        "rollback_recency",
        "template_churn",
    ]
