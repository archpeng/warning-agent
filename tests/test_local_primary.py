from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.fallback import run_local_primary_with_fallback
from app.investigator.local_primary import (
    LocalPrimaryInvestigator,
    build_investigation_id,
    local_primary_resident_lifecycle_payload,
    prewarm_local_primary_resident_service,
    reset_local_primary_resident_service,
)
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
EXPECTED_INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-investigation.json"


@pytest.fixture(autouse=True)
def _reset_local_primary_resident_runtime() -> None:
    reset_local_primary_resident_service()
    yield
    reset_local_primary_resident_service()


class FakeRealLocalPrimaryProvider:
    def investigate(self, request):
        result = _load_json(EXPECTED_INVESTIGATION_FIXTURE)
        result["model_name"] = "local-primary-real-v1"
        result["analysis_updates"]["notes"].append("local_primary_real_adapter_runtime_invoked")
        return result


class FakeOpenAICompatibleResponse:
    def __init__(self, payload: dict[str, object], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"unexpected status code: {self.status_code}")

    def json(self) -> dict[str, object]:
        return self._payload


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



def test_local_primary_auto_builds_real_adapter_provider_when_gate_ready(monkeypatch) -> None:
    import json as json_module

    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], headers: dict[str, str], timeout: float):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["payload"] = json
        return FakeOpenAICompatibleResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "summary": {
                                        "severity_band": "P1",
                                        "recommended_action": "page_owner",
                                        "confidence": 0.83,
                                        "reason_codes": ["error_rate_spike", "real_adapter_runtime"],
                                        "suspected_primary_cause": "payment gateway timeout saturation",
                                        "failure_chain_summary": "runtime auto-wired local-primary real adapter into checkout investigation.",
                                    },
                                    "hypotheses": [
                                        {
                                            "hypothesis": "payment gateway timeout saturation is driving checkout POST /api/pay failures",
                                            "confidence": 0.83,
                                            "supporting_reason_codes": ["error_rate_spike", "real_adapter_runtime"],
                                        }
                                    ],
                                    "unknowns": ["runtime auto-wire used fake OpenAI-compatible response"],
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.investigator.local_primary_openai_compat.httpx.post", fake_post)

    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000/v1",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "minimax-m2.7-highspeed",
        },
    )
    result = provider.investigate(plan.request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert provider.real_adapter_provider is not None
    assert provider.resident_lifecycle is not None
    assert provider.resident_lifecycle.state == "ready"
    assert provider.resident_lifecycle.provider_mode == "real_adapter_resident"
    assert not errors
    assert captured["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert captured["timeout"] == 45.0
    assert result["model_name"] == "minimax-m2.7-highspeed"
    assert "local_primary_real_adapter_response_mapped" in result["analysis_updates"]["notes"]
    assert result["unknowns"] == ["runtime auto-wire used fake OpenAI-compatible response"]



def test_local_primary_real_adapter_fail_closes_when_upstream_unavailable(monkeypatch) -> None:
    def fake_post(url: str, *, json: dict[str, object], headers: dict[str, str], timeout: float):
        raise RuntimeError("local_primary real adapter upstream unavailable")

    monkeypatch.setattr("app.investigator.local_primary_openai_compat.httpx.post", fake_post)

    packet = _build_packet()
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000/v1",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "minimax-m2.7-highspeed",
        },
    )
    result = run_local_primary_with_fallback(packet, decision, plan.request, provider=provider)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["investigator_tier"] == "local_primary_investigator"
    assert result["summary"]["recommended_action"] == "send_to_human_review"
    assert result["model_name"] == "local-primary-degraded-fallback"
    assert any(
        "local_primary real adapter upstream unavailable" in note
        for note in result["analysis_updates"]["notes"]
    )
    assert any(
        "local_primary real adapter upstream unavailable" in item
        for item in result["unknowns"]
    )



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



def test_local_primary_resident_prewarm_is_idempotent_for_same_boot_signature() -> None:
    first = prewarm_local_primary_resident_service(
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        prewarm_source="runtime_entry_boot",
    )
    second = prewarm_local_primary_resident_service(
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        prewarm_source="provider_init",
    )

    assert first.lifecycle == second.lifecycle
    assert local_primary_resident_lifecycle_payload(second.lifecycle) == {
        "service_mode": "resident_prewarm_on_boot",
        "invocation_scope": "needs_investigation_only",
        "startup_cost_policy": "excluded_from_per_warning_budget",
        "provider_mode": "smoke_resident",
        "state": "ready",
        "gate_state": "smoke_default",
        "model_name": "local-primary-smoke",
        "prewarm_completed_once": True,
        "prewarm_attempt_count": 1,
        "prewarm_source": "runtime_entry_boot",
        "reason": "smoke-default resident local-primary requires no external warmup",
    }



def test_local_primary_resident_prewarm_reports_not_ready_when_gate_env_is_incomplete() -> None:
    resolution = prewarm_local_primary_resident_service(
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
        repo_root=REPO_ROOT,
        env={"WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true"},
        prewarm_source="runtime_entry_boot",
    )

    assert resolution.real_adapter_provider is None
    assert resolution.lifecycle.provider_mode == "real_adapter_resident"
    assert resolution.lifecycle.state == "not_ready"
    assert resolution.lifecycle.gate_state == "missing_env"
    assert resolution.lifecycle.model_name == "gemma4-26b"
    assert resolution.lifecycle.prewarm_attempt_count == 1
    assert resolution.lifecycle.prewarm_source == "runtime_entry_boot"
    assert "local_primary real adapter gate enabled but missing env" in (resolution.lifecycle.reason or "")
