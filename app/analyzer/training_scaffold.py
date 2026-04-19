"""Offline learned-scorer training scaffold for W3 local trust upgrades."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from app.analyzer.calibrate import load_calibration_corpus
from app.analyzer.temporal_features import TEMPORAL_FEATURE_SET_VERSION
from app.analyzer.versioning import FAST_SCORER_ANALYZER_VERSION
from app.benchmarks.temporal_corpus import load_temporal_robustness_corpus

TRAINING_SCAFFOLD_SUMMARY_VERSION: Final = "local-analyzer-training-scaffold-summary.v1"
TRAINED_SCORER_ARTIFACT_VERSION: Final = "local-analyzer-trained-scorer.scaffold.v1"
TRAINED_SCORER_MODEL_FAMILY: Final = "logistic_regression"
TRAINED_SCORER_CALIBRATION_METHOD: Final = "platt_scaling"
MIN_ACCEPTED_LABELED_CASES: Final = 30
MIN_ACCEPTED_SEVERE_CASES: Final = 8
MIN_TEMPORAL_BASE_CASES: Final = 12
FEATURE_COLUMNS: Final[list[str]] = [
    "error_rate_regression",
    "latency_regression",
    "qps_shift",
    "anomaly_persistence",
    "deploy_recency",
    "rollback_recency",
    "template_churn",
]


class AcceptanceCheck(TypedDict):
    actual: float | bool
    expected: float | bool
    comparator: str
    passed: bool


class TrainingAcceptance(TypedDict):
    accepted: bool
    blockers: list[str]
    checks: dict[str, AcceptanceCheck]


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _metric_check(*, actual: float | bool, expected: float | bool, comparator: str, passed: bool) -> AcceptanceCheck:
    return {
        "actual": actual,
        "expected": expected,
        "comparator": comparator,
        "passed": passed,
    }


def run_trained_scorer_scaffold(
    *,
    calibration_corpus_path: str | Path,
    temporal_corpus_path: str | Path,
    summary_output_path: str | Path,
    artifact_output_path: str | Path,
    repo_root: Path = Path('.'),
) -> dict[str, object]:
    calibration_cases = load_calibration_corpus(calibration_corpus_path)
    _, temporal_cases = load_temporal_robustness_corpus(temporal_corpus_path)

    accepted_labeled_case_count = len(calibration_cases)
    accepted_labeled_severe_case_count = sum(1 for case in calibration_cases if case["label"] == "severe")
    temporal_base_case_count = len(temporal_cases)

    blockers: list[str] = []
    if accepted_labeled_case_count < MIN_ACCEPTED_LABELED_CASES:
        blockers.append("accepted_labeled_replay_corpus_below_w3_minimum")
    if accepted_labeled_severe_case_count < MIN_ACCEPTED_SEVERE_CASES:
        blockers.append("accepted_labeled_severe_cases_below_w3_minimum")
    if temporal_base_case_count < MIN_TEMPORAL_BASE_CASES:
        blockers.append("temporal_robustness_corpus_below_w3_minimum")

    training_ready = not blockers
    acceptance: TrainingAcceptance = {
        "accepted": training_ready,
        "blockers": [] if training_ready else ["training_scaffold_not_ready"],
        "checks": {
            "accepted_labeled_case_count": _metric_check(
                actual=accepted_labeled_case_count,
                expected=MIN_ACCEPTED_LABELED_CASES,
                comparator=">=",
                passed=accepted_labeled_case_count >= MIN_ACCEPTED_LABELED_CASES,
            ),
            "accepted_labeled_severe_case_count": _metric_check(
                actual=accepted_labeled_severe_case_count,
                expected=MIN_ACCEPTED_SEVERE_CASES,
                comparator=">=",
                passed=accepted_labeled_severe_case_count >= MIN_ACCEPTED_SEVERE_CASES,
            ),
            "temporal_base_case_count": _metric_check(
                actual=temporal_base_case_count,
                expected=MIN_TEMPORAL_BASE_CASES,
                comparator=">=",
                passed=temporal_base_case_count >= MIN_TEMPORAL_BASE_CASES,
            ),
        },
    }

    summary = {
        "summary_version": TRAINING_SCAFFOLD_SUMMARY_VERSION,
        "generated_at": _utc_now(),
        "feature_set_version": TEMPORAL_FEATURE_SET_VERSION,
        "base_analyzer_version": FAST_SCORER_ANALYZER_VERSION,
        "candidate_model_family": TRAINED_SCORER_MODEL_FAMILY,
        "candidate_calibration_method": TRAINED_SCORER_CALIBRATION_METHOD,
        "corpus_paths": {
            "calibration": str(calibration_corpus_path),
            "temporal_robustness": str(temporal_corpus_path),
        },
        "corpus_contract": {
            "accepted_labeled_case_count": accepted_labeled_case_count,
            "accepted_labeled_case_minimum": MIN_ACCEPTED_LABELED_CASES,
            "accepted_labeled_severe_case_count": accepted_labeled_severe_case_count,
            "accepted_labeled_severe_case_minimum": MIN_ACCEPTED_SEVERE_CASES,
            "temporal_base_case_count": temporal_base_case_count,
            "temporal_base_case_minimum": MIN_TEMPORAL_BASE_CASES,
            "training_ready": training_ready,
            "blocking_reasons": blockers,
        },
        "artifact_preview": {
            "artifact_version": TRAINED_SCORER_ARTIFACT_VERSION,
            "feature_columns": FEATURE_COLUMNS,
            "weights": None,
            "bias": None,
            "calibration_parameters": None,
        },
        "acceptance": acceptance,
        "notes": [
            "training scaffold only; artifact preview is frozen before sufficient data and runtime integration"
        ],
    }

    artifact = {
        "artifact_version": TRAINED_SCORER_ARTIFACT_VERSION,
        "generated_at": summary["generated_at"],
        "feature_set_version": TEMPORAL_FEATURE_SET_VERSION,
        "base_analyzer_version": FAST_SCORER_ANALYZER_VERSION,
        "model_family": TRAINED_SCORER_MODEL_FAMILY,
        "calibration_method": TRAINED_SCORER_CALIBRATION_METHOD,
        "training_state": "ready" if training_ready else "pending_more_labeled_data",
        "feature_columns": FEATURE_COLUMNS,
        "weights": None,
        "bias": None,
        "calibration_parameters": None,
    }

    summary_output_path = Path(summary_output_path)
    artifact_output_path = Path(artifact_output_path)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifact_output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
