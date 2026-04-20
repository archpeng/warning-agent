"""Training-facing trained scorer artifact assembly surface."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sklearn.linear_model import LogisticRegression

from app.analyzer.calibrate import load_calibration_corpus
from app.analyzer.corpus_packets import build_manual_replay_packet
from app.analyzer.temporal_features import TEMPORAL_FEATURE_SET_VERSION
from app.analyzer.trained_scorer_runtime import (
    TRAINED_SCORER_ARTIFACT_VERSION,
    TRAINED_SCORER_CALIBRATION_METHOD,
    TRAINED_SCORER_MODEL_FAMILY,
    TrainedScorerArtifact,
    _feature_vector,
)
from app.analyzer.versioning import FAST_SCORER_ANALYZER_VERSION, TRAINED_SCORER_ANALYZER_VERSION
from app.benchmarks.temporal_corpus import load_temporal_robustness_corpus



def train_trained_scorer_artifact(
    *,
    calibration_corpus_path: str | Path,
    temporal_corpus_path: str | Path,
    output_path: str | Path,
    repo_root: Path = Path("."),
) -> TrainedScorerArtifact:
    samples: list[list[float]] = []
    labels: list[int] = []

    for row, label in _iter_calibration_training_rows(calibration_corpus_path=calibration_corpus_path, repo_root=repo_root):
        samples.append(row)
        labels.append(label)
    for row, label in _iter_temporal_training_rows(temporal_corpus_path=temporal_corpus_path, repo_root=repo_root):
        samples.append(row)
        labels.append(label)

    base_model = LogisticRegression(random_state=0, solver="liblinear", max_iter=1000)
    base_model.fit(samples, labels)
    raw_scores = base_model.decision_function(samples)

    calibrator = LogisticRegression(random_state=0, solver="liblinear", max_iter=1000)
    calibrator.fit([[score] for score in raw_scores], labels)

    artifact: TrainedScorerArtifact = {
        "artifact_version": TRAINED_SCORER_ARTIFACT_VERSION,
        "generated_at": _utc_now(),
        "feature_set_version": TEMPORAL_FEATURE_SET_VERSION,
        "base_analyzer_version": FAST_SCORER_ANALYZER_VERSION,
        "analyzer_version": TRAINED_SCORER_ANALYZER_VERSION,
        "model_family": TRAINED_SCORER_MODEL_FAMILY,
        "calibration_method": TRAINED_SCORER_CALIBRATION_METHOD,
        "training_state": "ready",
        "feature_columns": [
            "error_rate_regression",
            "latency_regression",
            "qps_shift",
            "anomaly_persistence",
            "deploy_recency",
            "rollback_recency",
            "template_churn",
        ],
        "training_case_count": len(labels),
        "severe_case_count": sum(labels),
        "weights": [float(value) for value in base_model.coef_[0]],
        "bias": float(base_model.intercept_[0]),
        "calibration_parameters": {
            "slope": float(calibrator.coef_[0][0]),
            "intercept": float(calibrator.intercept_[0]),
        },
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact



def _iter_calibration_training_rows(
    *,
    calibration_corpus_path: str | Path,
    repo_root: Path,
) -> list[tuple[list[float], int]]:
    rows: list[tuple[list[float], int]] = []
    for case in load_calibration_corpus(calibration_corpus_path):
        packet = build_manual_replay_packet(
            repo_root=repo_root,
            replay_fixture=case["replay_fixture"],
            evidence_fixture=case["evidence_fixture"],
        )
        rows.append((_feature_vector(packet), 1 if case["label"] == "severe" else 0))
    return rows



def _iter_temporal_training_rows(
    *,
    temporal_corpus_path: str | Path,
    repo_root: Path,
) -> list[tuple[list[float], int]]:
    rows: list[tuple[list[float], int]] = []
    _, cases = load_temporal_robustness_corpus(temporal_corpus_path)
    for case in cases:
        replay_fixture = str(case["replay_fixture"])
        for variant in case["variants"]:
            packet_v1 = build_manual_replay_packet(
                repo_root=repo_root,
                replay_fixture=replay_fixture,
                evidence_fixture=str(variant["evidence_fixture"]),
            )
            packet_v2 = {
                **packet_v1,
                "schema_version": "incident-packet.v2",
                "temporal_context": variant["temporal_context"],
            }
            rows.append((_feature_vector(packet_v2), 1 if variant["expected_severity_band"] in {"P1", "P2"} else 0))
    return rows



def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
