from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.analyzer.base import build_decision_id, extract_features, load_thresholds
from app.analyzer.fast_scorer import FastScorer
from app.analyzer.contracts import load_schema as load_decision_schema
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
EXPECTED_DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_packet() -> dict:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(
        replay["alert_payload"],
        candidate_source="manual_replay",
    )
    return build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))


def test_feature_extraction_matches_expected_checkout_signals() -> None:
    packet = _build_packet()
    retrieval_hits = _load_json(EXPECTED_DECISION_FIXTURE)["retrieval_hits"]

    features = extract_features(packet, retrieval_hits)

    assert features.error_rate_spike == 0.95
    assert features.latency_spike == 0.995
    assert features.novelty_signal == 0.91
    assert features.severe_retrieval_similarity == 0.82
    assert features.blast_radius_score == 0.88
    assert features.evidence_coverage == 1.0
    assert features.recent_deploy == 1.0


def test_fast_scorer_produces_deterministic_schema_valid_decision() -> None:
    packet = _build_packet()
    expected = _load_json(EXPECTED_DECISION_FIXTURE)
    scorer = FastScorer(load_thresholds())

    decision = scorer.score_packet(packet, retrieval_hits=expected["retrieval_hits"])
    validator = Draft202012Validator(load_decision_schema())
    errors = sorted(validator.iter_errors(decision), key=lambda error: error.json_path)

    assert not errors
    assert decision == expected
    assert build_decision_id(packet) == expected["decision_id"]
