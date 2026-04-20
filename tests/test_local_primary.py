from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.fallback import run_local_primary_with_fallback
from app.investigator.local_primary import LocalPrimaryInvestigator, build_investigation_id
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
EXPECTED_INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-investigation.json"


class FakeRealLocalPrimaryProvider:
    def investigate(self, request):
        result = _load_json(EXPECTED_INVESTIGATION_FIXTURE)
        result["model_name"] = "local-primary-real-v1"
        result["analysis_updates"]["notes"].append("local_primary_real_adapter_runtime_invoked")
        return result


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_packet() -> dict:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    return build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))


def test_local_primary_provider_produces_deterministic_schema_valid_result() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    expected = _load_json(EXPECTED_INVESTIGATION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
    )
    result = provider.investigate(plan.request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert provider.tools is not None
    assert provider.tools.repo_root == REPO_ROOT
    assert result == expected
    assert build_investigation_id(packet) == expected["investigation_id"]
    assert result["routing"]["owner_hint"] == "payments-oncall"
    assert result["summary"]["investigation_used"] is True
    assert result["unknowns"]
    assert "bounded_repo_search_used" in result["analysis_updates"]["notes"]
    assert "tool_calls_used=1" in result["analysis_updates"]["notes"]
    assert any(note.startswith("repo_search_hit_count=") for note in result["analysis_updates"]["notes"])
    assert provider.tools.usage_snapshot().calls_used == 0



def test_local_primary_can_use_real_adapter_provider_when_gate_ready() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        real_adapter_provider=FakeRealLocalPrimaryProvider(),
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "local-primary-real-v1",
        },
    )
    result = provider.investigate(plan.request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["model_name"] == "local-primary-real-v1"
    assert "local_primary_real_adapter_runtime_invoked" in result["analysis_updates"]["notes"]



def test_local_primary_real_adapter_gate_fails_closed_when_required_env_is_missing() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        env={"WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true"},
    )
    result = run_local_primary_with_fallback(packet, decision, plan.request, provider=provider)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["investigator_tier"] == "local_primary_investigator"
    assert result["summary"]["recommended_action"] == "send_to_human_review"
    assert any(
        "local_primary real adapter gate enabled but missing env" in note
        for note in result["analysis_updates"]["notes"]
    )
    assert any(
        "local_primary real adapter gate enabled but missing env" in item
        for item in result["unknowns"]
    )
