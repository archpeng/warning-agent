"""Offline retrain / evaluate / compare scaffold for warning-agent W4."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from sklearn.linear_model import LogisticRegression

from app.analyzer.base import load_thresholds, round_score
from app.analyzer.fast_scorer import FastScorer
from app.analyzer.runtime import resolve_runtime_scorer
from app.analyzer.temporal_features import extract_temporal_features
from app.analyzer.trained_scorer import TrainedScorer, TrainedScorerArtifact, ensure_packet_v2
from app.analyzer.training_scaffold import FEATURE_COLUMNS
from app.analyzer.versioning import FAST_SCORER_ANALYZER_VERSION
from app.benchmarks.temporal_corpus import load_temporal_robustness_corpus
from app.feedback.corpus import (
    DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH,
    FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION,
    FeedbackCompareCorpus,
)
from app.packet.builder import build_incident_packet_from_bundle, build_incident_packet_v2
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture

COMPARE_SUMMARY_VERSION: Final = "local-analyzer-feedback-compare-summary.v1"
DEFAULT_COMPARE_SUMMARY_PATH: Final = Path("data/benchmarks/local-analyzer-feedback-compare-summary.json")
DEFAULT_CANDIDATE_ARTIFACT_PATH: Final = Path("data/models/local-analyzer-trained-scorer.candidate.json")
CANDIDATE_ANALYZER_VERSION: Final = "trained-scorer-feedback-candidate-2026-04-19"


class ModelMetrics(TypedDict):
    total_cases: int
    severe_case_count: int
    severe_recall: float
    investigation_precision: float
    investigation_candidate_rate: float
    average_confidence: float
    brier_score: float


class CompareSummary(TypedDict):
    summary_version: str
    generated_at: str
    corpus_path: str
    corpus_contract: dict[str, int]
    models: dict[str, dict[str, object]]
    provisional_decision: dict[str, object]
    notes: list[str]


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _feature_row(packet: dict[str, object]) -> list[float]:
    vector = extract_temporal_features(ensure_packet_v2(packet))
    return [
        float(vector.error_rate_regression),
        float(vector.latency_regression),
        float(vector.qps_shift),
        float(vector.anomaly_persistence),
        float(vector.deploy_recency),
        float(vector.rollback_recency),
        float(vector.template_churn),
    ]


def _sigmoid(value: float) -> float:
    import math

    if value >= 0:
        exp = math.exp(-value)
        return 1.0 / (1.0 + exp)
    exp = math.exp(value)
    return exp / (1.0 + exp)


def load_feedback_compare_corpus(path: str | Path) -> FeedbackCompareCorpus:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported feedback compare corpus schema_version '{payload.get('schema_version')}'"
        )
    return payload


def _evaluate_scorer(*, scorer: object, cases: list[dict[str, object]]) -> ModelMetrics:
    predicted_severe_count = 0
    predicted_investigation_count = 0
    severe_true_positives = 0
    investigation_true_positives = 0
    severe_case_count = 0
    confidence_sum = 0.0
    brier_sum = 0.0

    for case in cases:
        label = str(case["label"])
        packet = case["packet"]
        retrieval_hits = list(case["retrieval_hits"])
        decision = scorer.score_packet(packet, retrieval_hits=retrieval_hits)  # type: ignore[attr-defined]
        is_severe = label == "severe"
        predicted_severe = decision["severity_band"] in {"P1", "P2"}
        predicted_investigation = bool(decision["needs_investigation"])
        probability = float(decision["severity_score"])
        target = 1.0 if is_severe else 0.0

        severe_case_count += int(is_severe)
        predicted_severe_count += int(predicted_severe)
        predicted_investigation_count += int(predicted_investigation)
        severe_true_positives += int(is_severe and predicted_severe)
        investigation_true_positives += int(is_severe and predicted_investigation)
        confidence_sum += float(decision["confidence"])
        brier_sum += (probability - target) ** 2

    total_cases = len(cases)
    severe_recall = round_score(severe_true_positives / severe_case_count) if severe_case_count else 0.0
    investigation_precision = (
        round_score(investigation_true_positives / predicted_investigation_count)
        if predicted_investigation_count
        else 0.0
    )
    investigation_candidate_rate = round_score(predicted_investigation_count / total_cases) if total_cases else 0.0
    average_confidence = round_score(confidence_sum / total_cases) if total_cases else 0.0
    brier_score = round_score(brier_sum / total_cases) if total_cases else 0.0

    return {
        "total_cases": total_cases,
        "severe_case_count": severe_case_count,
        "severe_recall": severe_recall,
        "investigation_precision": investigation_precision,
        "investigation_candidate_rate": investigation_candidate_rate,
        "average_confidence": average_confidence,
        "brier_score": brier_score,
    }


def _temporal_training_rows(*, temporal_corpus_path: Path, repo_root: Path) -> tuple[list[list[float]], list[int]]:
    samples: list[list[float]] = []
    labels: list[int] = []
    _, cases = load_temporal_robustness_corpus(temporal_corpus_path)
    for case in cases:
        replay = load_manual_replay_fixture(repo_root / case["replay_fixture"])
        normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
        for variant in case["variants"]:
            evidence = json.loads((repo_root / variant["evidence_fixture"]).read_text(encoding="utf-8"))
            packet_v1 = build_incident_packet_from_bundle(normalized, evidence)
            packet_v2 = build_incident_packet_v2(packet_v1, temporal_context=variant["temporal_context"])
            samples.append(_feature_row(packet_v2))
            labels.append(1 if variant["expected_severity_band"] in {"P1", "P2"} else 0)
    return samples, labels


def train_candidate_from_compare_corpus(
    *,
    corpus: FeedbackCompareCorpus,
    temporal_corpus_path: Path,
    output_path: Path,
    repo_root: Path,
) -> TrainedScorerArtifact:
    samples = [_feature_row(case["packet"]) for case in corpus["cases"]]
    labels = [1 if case["label"] == "severe" else 0 for case in corpus["cases"]]
    temporal_samples, temporal_labels = _temporal_training_rows(temporal_corpus_path=temporal_corpus_path, repo_root=repo_root)
    samples.extend(temporal_samples)
    labels.extend(temporal_labels)

    base_model = LogisticRegression(random_state=0, solver="liblinear", max_iter=1000)
    base_model.fit(samples, labels)
    raw_scores = base_model.decision_function(samples)

    calibrator = LogisticRegression(random_state=0, solver="liblinear", max_iter=1000)
    calibrator.fit([[score] for score in raw_scores], labels)

    artifact: TrainedScorerArtifact = {
        "artifact_version": "local-analyzer-trained-scorer.v1",
        "generated_at": _utc_now(),
        "feature_set_version": "temporal-context-v2.features.v1",
        "base_analyzer_version": FAST_SCORER_ANALYZER_VERSION,
        "analyzer_version": CANDIDATE_ANALYZER_VERSION,
        "model_family": "logistic_regression",
        "calibration_method": "platt_scaling",
        "training_state": "ready",
        "feature_columns": list(FEATURE_COLUMNS),
        "training_case_count": len(labels),
        "severe_case_count": sum(labels),
        "weights": [float(value) for value in base_model.coef_[0]],
        "bias": float(base_model.intercept_[0]),
        "calibration_parameters": {
            "slope": float(calibrator.coef_[0][0]),
            "intercept": float(calibrator.intercept_[0]),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact


def _provisional_decision(*, current_metrics: ModelMetrics, candidate_metrics: ModelMetrics) -> dict[str, object]:
    candidate_not_worse = (
        candidate_metrics["severe_recall"] >= current_metrics["severe_recall"]
        and candidate_metrics["brier_score"] <= current_metrics["brier_score"]
    )
    preferred_model = "candidate_hold"
    reasons: list[str] = ["no_auto_promotion_in_s3a"]
    if candidate_not_worse and candidate_metrics["investigation_precision"] >= current_metrics["investigation_precision"]:
        preferred_model = "candidate_ready_for_review"
        reasons.append("candidate_not_worse_than_current_on_compare_corpus")
    else:
        reasons.append("candidate_did_not_clear_non_regression_compare_rule")

    return {
        "preferred_model": preferred_model,
        "reasons": reasons,
    }


def run_feedback_retrain_compare(
    *,
    corpus_path: str | Path = DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH,
    summary_output_path: str | Path = DEFAULT_COMPARE_SUMMARY_PATH,
    candidate_artifact_output_path: str | Path = DEFAULT_CANDIDATE_ARTIFACT_PATH,
    temporal_corpus_path: str | Path = Path("fixtures/evidence/local-analyzer-temporal-robustness-corpus.json"),
    repo_root: Path = Path("."),
) -> CompareSummary:
    repo_root = Path(repo_root)
    corpus_path = Path(corpus_path)
    if not corpus_path.is_absolute():
        corpus_path = repo_root / corpus_path
    corpus = load_feedback_compare_corpus(corpus_path)
    thresholds = load_thresholds(repo_root / "configs" / "thresholds.yaml")

    fast_scorer = FastScorer(thresholds)
    current_scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=thresholds)
    candidate_artifact = train_candidate_from_compare_corpus(
        corpus=corpus,
        temporal_corpus_path=repo_root / temporal_corpus_path,
        output_path=(repo_root / candidate_artifact_output_path) if not Path(candidate_artifact_output_path).is_absolute() else Path(candidate_artifact_output_path),
        repo_root=repo_root,
    )
    candidate_scorer = TrainedScorer.from_artifact_path(
        (repo_root / candidate_artifact_output_path) if not Path(candidate_artifact_output_path).is_absolute() else Path(candidate_artifact_output_path),
        thresholds=thresholds,
    )

    fast_metrics = _evaluate_scorer(scorer=fast_scorer, cases=corpus["cases"])
    current_metrics = _evaluate_scorer(scorer=current_scorer, cases=corpus["cases"])
    candidate_metrics = _evaluate_scorer(scorer=candidate_scorer, cases=corpus["cases"])

    summary: CompareSummary = {
        "summary_version": COMPARE_SUMMARY_VERSION,
        "generated_at": _utc_now(),
        "corpus_path": str(corpus_path),
        "corpus_contract": corpus["corpus_contract"],
        "models": {
            "fast_scorer": {
                "analyzer_version": FAST_SCORER_ANALYZER_VERSION,
                "metrics": fast_metrics,
            },
            "current_runtime": {
                "analyzer_version": getattr(current_scorer, "analyzer_version", "unknown"),
                "metrics": current_metrics,
            },
            "candidate_retrained": {
                "analyzer_version": candidate_artifact["analyzer_version"],
                "artifact_path": str((repo_root / candidate_artifact_output_path) if not Path(candidate_artifact_output_path).is_absolute() else Path(candidate_artifact_output_path)),
                "training_case_count": candidate_artifact["training_case_count"],
                "severe_case_count": candidate_artifact["severe_case_count"],
                "metrics": candidate_metrics,
            },
        },
        "provisional_decision": _provisional_decision(
            current_metrics=current_metrics,
            candidate_metrics=candidate_metrics,
        ),
        "notes": [
            "candidate retraining currently evaluates on the assembled compare corpus used for feedback bootstrap; reality-audit review remains mandatory before any promotion",
        ],
    }

    summary_output_path = Path(summary_output_path)
    if not summary_output_path.is_absolute():
        summary_output_path = repo_root / summary_output_path
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
