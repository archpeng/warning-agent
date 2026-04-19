from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.base import load_thresholds
from app.analyzer.trained_scorer import TrainedScorer, train_trained_scorer_artifact
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"
TEMPORAL_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json"
CHECKOUT_REPLAY = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
CHECKOUT_EVIDENCE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
CATALOG_REPLAY = REPO_ROOT / "fixtures" / "replay" / "manual-replay.catalog.latency-warning.json"
CATALOG_EVIDENCE = REPO_ROOT / "fixtures" / "evidence" / "catalog.packet-input.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_packet(replay_path: Path, evidence_path: Path) -> dict[str, object]:
    replay = load_manual_replay_fixture(replay_path)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    return build_incident_packet_from_bundle(normalized, _load_json(evidence_path))


def test_train_trained_scorer_artifact_writes_runtime_ready_model(tmp_path: Path) -> None:
    artifact_path = tmp_path / "local-analyzer-trained-scorer.v1.json"

    artifact = train_trained_scorer_artifact(
        calibration_corpus_path=CALIBRATION_CORPUS,
        temporal_corpus_path=TEMPORAL_CORPUS,
        output_path=artifact_path,
        repo_root=REPO_ROOT,
    )

    written = _load_json(artifact_path)

    assert artifact == written
    assert artifact["artifact_version"] == "local-analyzer-trained-scorer.v1"
    assert artifact["training_state"] == "ready"
    assert artifact["feature_set_version"] == "temporal-context-v2.features.v1"
    assert artifact["training_case_count"] == 66
    assert artifact["severe_case_count"] == 23
    assert artifact["weights"] is not None
    assert len(artifact["weights"]) == 7
    assert artifact["bias"] is not None
    assert artifact["calibration_parameters"] is not None


def test_trained_scorer_scores_severe_and_benign_packets_from_runtime_artifact(tmp_path: Path) -> None:
    artifact_path = tmp_path / "local-analyzer-trained-scorer.v1.json"
    train_trained_scorer_artifact(
        calibration_corpus_path=CALIBRATION_CORPUS,
        temporal_corpus_path=TEMPORAL_CORPUS,
        output_path=artifact_path,
        repo_root=REPO_ROOT,
    )
    scorer = TrainedScorer.from_artifact_path(
        artifact_path,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    )

    severe_decision = scorer.score_packet(_build_packet(CHECKOUT_REPLAY, CHECKOUT_EVIDENCE), retrieval_hits=[])
    benign_decision = scorer.score_packet(_build_packet(CATALOG_REPLAY, CATALOG_EVIDENCE), retrieval_hits=[])

    assert severe_decision["analyzer_family"] == "hybrid"
    assert severe_decision["analyzer_version"] == "trained-scorer-2026-04-19"
    assert severe_decision["severity_score"] >= 0.75
    assert severe_decision["severity_band"] in {"P1", "P2"}
    assert severe_decision["needs_investigation"] is True

    assert benign_decision["analyzer_family"] == "hybrid"
    assert benign_decision["analyzer_version"] == "trained-scorer-2026-04-19"
    assert benign_decision["severity_score"] < 0.5
    assert benign_decision["severity_band"] == "P4"
    assert benign_decision["needs_investigation"] is False
