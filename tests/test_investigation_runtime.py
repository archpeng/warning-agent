from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.investigator.cloud_fallback import CloudFallbackInvestigator
from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.router import load_investigator_routing_config, plan_cloud_fallback
from app.investigator.runtime import run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.reports.markdown_builder import render_alert_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
LOCAL_INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-investigation.json"


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


def test_plan_cloud_fallback_only_escalates_low_confidence_unresolved_results() -> None:
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    local_result = _load_json(LOCAL_INVESTIGATION_FIXTURE)
    low_confidence_result = copy.deepcopy(local_result)
    low_confidence_result["summary"]["confidence"] = 0.64

    keep_local = plan_cloud_fallback(local_result, config=config)
    escalate = plan_cloud_fallback(low_confidence_result, config=config)

    assert config.routing.allow_cloud_fallback is True
    assert config.cloud_fallback.enabled is True
    assert keep_local.should_escalate is False
    assert keep_local.trigger_reasons == ()
    assert escalate.should_escalate is True
    assert set(escalate.trigger_reasons) == {
        "local_confidence_below_cloud_gate",
        "unresolved_unknowns_cloud_gate",
    }


def test_run_investigation_runtime_keeps_local_result_when_cloud_gate_is_not_hit() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)

    execution = run_investigation_runtime(
        packet,
        decision,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
    )

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(execution.final_result), key=lambda error: error.json_path)

    assert execution.route_plan.should_investigate is True
    assert execution.local_result is not None
    assert execution.cloud_plan is not None
    assert execution.cloud_plan.should_escalate is False
    assert execution.cloud_audit is None
    assert not errors
    assert execution.final_result["investigator_tier"] == "local_primary_investigator"


def test_run_investigation_runtime_escalates_degraded_local_result_to_cloud() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)

    execution = run_investigation_runtime(
        packet,
        decision,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        local_provider=CrashingLocalPrimaryProvider(),
    )

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(execution.final_result), key=lambda error: error.json_path)

    assert execution.local_result is not None
    assert execution.local_result["investigator_tier"] == "local_primary_investigator"
    assert execution.cloud_plan is not None
    assert execution.cloud_plan.should_escalate is True
    assert execution.cloud_audit is not None
    assert execution.cloud_audit.fallback_used is False
    assert not errors
    assert execution.final_result["investigator_tier"] == "cloud_fallback_investigator"

    report = render_alert_report(packet, decision, execution.final_result)
    assert "investigation_stage: cloud_fallback" in report



def test_run_investigation_runtime_fail_closes_when_cloud_real_adapter_gate_is_ready_but_client_missing() -> None:
    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    cloud_provider = CloudFallbackInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.openai.example/v1",
            "OPENAI_API_KEY": "secret-token",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-4o-mini",
        },
    )

    execution = run_investigation_runtime(
        packet,
        decision,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        local_provider=CrashingLocalPrimaryProvider(),
        cloud_provider=cloud_provider,
    )

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(execution.final_result), key=lambda error: error.json_path)

    assert execution.cloud_audit is not None
    assert execution.cloud_audit.fallback_used is True
    assert not errors
    assert execution.final_result["investigator_tier"] == "local_primary_investigator"
    assert execution.final_result["summary"]["recommended_action"] == "send_to_human_review"
    assert any(
        "cloud_fallback real adapter gate ready but client unavailable" in note
        for note in execution.final_result["analysis_updates"]["notes"]
    )
