from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.base import extract_features
from app.analyzer.internal_records import (
    build_decision_audit_record,
    build_sidecar_assist_packet,
    decision_audit_record_payload,
    sidecar_assist_packet_payload,
)
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"



def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))



def _build_packet() -> dict[str, object]:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    return build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))



def test_build_sidecar_assist_packet_exposes_query_terms_and_value_hint() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    features = extract_features(packet, decision["retrieval_hits"])

    assist = build_sidecar_assist_packet(packet, features=features, decision=decision)
    payload = sidecar_assist_packet_payload(assist)

    assert assist.packet_id == packet["packet_id"]
    assert assist.service == packet["service"]
    assert "checkout" in assist.suggested_query_terms
    assert assist.investigation_value_hint == "high"
    assert "novelty_high" in assist.ambiguity_flags
    assert payload["notes"] == ["minimal_internal_assist_groundwork"]



def test_build_decision_audit_record_surfaces_top_signals_without_changing_canonical_decision() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    features = extract_features(packet, decision["retrieval_hits"])

    record = build_decision_audit_record(packet=packet, decision=decision, features=features)
    payload = decision_audit_record_payload(record)

    assert record.decision_id == decision["decision_id"]
    assert record.packet_id == packet["packet_id"]
    assert record.needs_investigation is True
    assert record.expected_value_hint == "high"
    assert "error_rate_spike" in record.top_contributing_signals
    assert "blast_radius" in record.top_contributing_signals
    assert "novelty_high" in record.ambiguity_flags
    assert any(item.startswith("confidence=") for item in record.confidence_context)
    assert payload["decision_id"] == decision["decision_id"]
    assert payload["recommended_action"] == decision["recommended_action"]
