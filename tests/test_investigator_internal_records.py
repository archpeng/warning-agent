from __future__ import annotations

import json
from pathlib import Path

from app.investigator.cloud_fallback import build_cloud_fallback_request
from app.investigator.internal_records import (
    action_trace_payload,
    build_action_trace,
    build_compressed_investigation_brief,
    build_investigation_evidence_pack,
    compressed_investigation_brief_payload,
    investigation_evidence_pack_payload,
)
from app.investigator.local_primary import LocalPrimaryInvestigator, reset_local_primary_resident_service
from app.investigator.router import load_investigator_routing_config, plan_investigation
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



def _build_local_result() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    reset_local_primary_resident_service()
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(REPO_ROOT / "configs" / "escalation.yaml")
    local_result = provider.investigate(plan.request)
    return packet, decision, local_result



def test_build_investigation_evidence_pack_collects_noncanonical_learning_refs() -> None:
    _, _, local_result = _build_local_result()

    pack = build_investigation_evidence_pack(local_result)
    payload = investigation_evidence_pack_payload(pack)

    assert pack.packet_id == local_result["packet_id"]
    assert pack.decision_id == local_result["decision_id"]
    assert "error_rate_spike" in pack.strongest_signal_notes
    assert payload["packet_id"] == local_result["packet_id"]
    assert payload["prometheus_ref_ids"] == local_result["evidence_refs"]["prometheus_ref_ids"]



def test_build_compressed_investigation_brief_wraps_cloud_handoff_without_changing_contract() -> None:
    packet, decision, local_result = _build_local_result()

    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    brief = build_compressed_investigation_brief(request)
    payload = compressed_investigation_brief_payload(brief)

    assert brief.packet_id == packet["packet_id"]
    assert brief.parent_investigation_id == local_result["investigation_id"]
    assert "# Cloud Fallback Handoff" in brief.handoff_markdown
    assert brief.handoff_tokens_estimate == request.handoff_tokens_estimate
    assert payload["carry_reason_codes"] == list(request.carry_reason_codes)



def test_build_action_trace_records_local_then_cloud_progression() -> None:
    packet, decision, local_result = _build_local_result()

    trace = build_action_trace(
        packet_id=packet["packet_id"],
        decision_id=decision["decision_id"],
        route_selected_provider="local_primary",
        cloud_trigger_reasons=("local_confidence_below_cloud_gate",),
        final_result={
            **local_result,
            "investigator_tier": "cloud_fallback_investigator",
            "analysis_updates": {**local_result["analysis_updates"], "notes": ["cloud_fallback_smoke_result"]},
        },
    )
    payload = action_trace_payload(trace)

    assert trace.packet_id == packet["packet_id"]
    assert trace.decision_id == decision["decision_id"]
    assert [step["action"] for step in payload["steps"]] == [
        "select_local_primary",
        "escalate_to_cloud_fallback",
        "run_cloud_fallback",
    ]
    assert payload["stop_reason"] == "final_result_available"
