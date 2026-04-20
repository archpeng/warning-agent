from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.fallback import run_local_primary_with_fallback
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.reports.markdown_builder import render_alert_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"


class CrashingLocalPrimaryProvider:
    def investigate(self, request):
        raise RuntimeError("local tool budget exhausted before follow-up completed")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_packet() -> dict:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    return build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))


def test_degraded_local_fallback_returns_schema_valid_partial_result_and_report() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)

    result = run_local_primary_with_fallback(
        packet,
        decision,
        plan.request,
        provider=CrashingLocalPrimaryProvider(),
    )

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["investigator_tier"] == "local_primary_investigator"
    assert result["summary"]["recommended_action"] == "send_to_human_review"
    assert result["analysis_updates"]["fallback_invocation_was_correct"] is True
    assert result["analysis_updates"]["recommended_action_changed"] is True
    assert "degraded_local_fallback" in result["analysis_updates"]["notes"]
    assert "local_primary_provider_mode=deterministic_smoke" in result["analysis_updates"]["notes"]
    assert "local_primary_current_smoke_model=local-primary-smoke" in result["analysis_updates"]["notes"]
    assert "local_primary_future_real_adapter=local_vllm_openai_compat" in result["analysis_updates"]["notes"]
    assert (
        "local_primary_future_real_adapter_enabled_env="
        "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED"
    ) in result["analysis_updates"]["notes"]
    assert "fail_closed_to=send_to_human_review" in result["analysis_updates"]["notes"]
    assert any("local tool budget exhausted" in item for item in result["unknowns"])

    report = render_alert_report(packet, decision, result)
    assert "investigation_stage: local_primary" in report
    assert "degraded local path" in report
    assert "immediate action: `send_to_human_review`" in report
