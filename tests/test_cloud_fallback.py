from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.investigator.cloud_fallback import (
    CloudFallbackClientResponse,
    CloudFallbackGuardSnapshot,
    CloudFallbackHypothesis,
    CloudFallbackInvestigator,
    build_cloud_client_request,
    build_cloud_fallback_request,
    evaluate_cloud_fallback_guards,
    run_cloud_fallback_with_local_fallback,
)
from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.local_primary import LocalPrimaryInvestigator
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.reports.markdown_builder import render_alert_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
EXPECTED_LOCAL_INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-investigation.json"
EXPECTED_CLOUD_INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.cloud-investigation.json"


@pytest.fixture(autouse=True)
def _reset_local_primary_resident_runtime() -> None:
    from app.investigator.local_primary import reset_local_primary_resident_service

    reset_local_primary_resident_service()
    yield
    reset_local_primary_resident_service()


class CrashingCloudFallbackClient:
    def investigate(self, request):
        raise RuntimeError("vendor timeout during bounded cloud review")


class FakeRealCloudFallbackClient:
    def investigate(self, request):
        return CloudFallbackClientResponse(
            severity_band="P1",
            recommended_action="page_owner",
            confidence=0.91,
            suspected_primary_cause="real adapter confirmed db timeout on order lookup",
            failure_chain_summary=(
                "real adapter reviewed the bounded local handoff and confirmed db timeout on order lookup"
            ),
            hypotheses=(
                CloudFallbackHypothesis(
                    hypothesis="real adapter confirms the checkout timeout regression",
                    confidence=0.91,
                    supporting_reason_codes=("real_adapter_runtime",),
                ),
            ),
            unknowns=("real adapter local proof only; remote rollout remains gated",),
            notes=("cloud_fallback_real_adapter_runtime_invoked",),
        )


class FakeOpenAIResponsesResponse:
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


def _build_local_investigation(packet: dict) -> tuple[dict, dict, dict]:
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)
    provider = LocalPrimaryInvestigator.from_config(REPO_ROOT / "configs" / "escalation.yaml")
    local_result = provider.investigate(plan.request)
    return decision, config, local_result


def test_build_cloud_fallback_request_creates_bounded_handoff_contract() -> None:
    packet = _build_packet()
    decision, config, local_result = _build_local_investigation(packet)

    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    client_request = build_cloud_client_request(request)

    expected_local = _load_json(EXPECTED_LOCAL_INVESTIGATION_FIXTURE)
    assert local_result == expected_local
    assert request.parent_investigation["investigation_id"] == expected_local["investigation_id"]
    assert request.handoff_tokens_estimate <= config.cloud_fallback.budget.max_handoff_tokens
    assert request.carry_reason_codes == tuple(expected_local["summary"]["reason_codes"])
    assert "# Cloud Fallback Handoff" in request.handoff_markdown
    assert expected_local["summary"]["suspected_primary_cause"] in request.handoff_markdown

    assert set(vars(client_request)) == {
        "investigation_id",
        "parent_investigation_id",
        "packet_id",
        "decision_id",
        "handoff_markdown",
        "handoff_tokens_estimate",
        "carry_reason_codes",
        "retrieval_packet_ids",
        "prometheus_query_refs",
        "signoz_query_refs",
        "trace_ids",
        "repo_candidates",
        "code_refs",
    }
    assert client_request.handoff_markdown == request.handoff_markdown
    assert client_request.retrieval_packet_ids == ("ipk_checkout_post_pay_20260411t110000z",)
    assert client_request.prometheus_query_refs == ("prom://query/high_error_rate_window_300s",)
    assert client_request.signoz_query_refs == ("signoz://trace/query-123", "signoz://logs/query-456")
    assert client_request.code_refs == (
        "services/checkout/post_api_pay.py",
        "repos/checkout-service/post_api_pay",
    )


def test_cloud_fallback_provider_produces_schema_valid_result_and_cloud_report() -> None:
    packet = _build_packet()
    decision, config, local_result = _build_local_investigation(packet)
    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    expected = _load_json(EXPECTED_CLOUD_INVESTIGATION_FIXTURE)

    provider = CloudFallbackInvestigator.from_config(REPO_ROOT / "configs" / "escalation.yaml")
    result = provider.investigate(request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["schema_version"] == expected["schema_version"]
    assert result["investigator_tier"] == expected["investigator_tier"]
    assert result["model_provider"] == expected["model_provider"]
    assert result["model_name"] == expected["model_name"]
    assert result["parent_investigation_id"] == local_result["investigation_id"]
    assert result["summary"] == expected["summary"]
    assert result["hypotheses"] == expected["hypotheses"]
    assert "cloud_fallback_target_model_provider=neko_api_openai" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_target_model_name=gpt-5.4-xhigh" in result["analysis_updates"]["notes"]
    assert result["compressed_handoff"]["handoff_tokens_estimate"] <= config.cloud_fallback.budget.max_handoff_tokens
    assert result["analysis_updates"]["fallback_invocation_was_correct"] is True

    report = render_alert_report(packet, decision, result)
    assert "investigation_stage: cloud_fallback" in report
    assert "cloud fallback reviewed the bounded local handoff" in report


def test_evaluate_cloud_fallback_guards_reports_pass_and_failure() -> None:
    _, config, _ = _build_local_investigation(_build_packet())

    accepted = evaluate_cloud_fallback_guards(
        CloudFallbackGuardSnapshot(
            total_packets=20,
            investigated_packets=4,
            cloud_fallback_invocation_count=1,
            wall_time_seconds=(18.0,),
            handoff_tokens_estimates=(236,),
        ),
        budget=config.cloud_fallback.budget,
    )
    rejected = evaluate_cloud_fallback_guards(
        CloudFallbackGuardSnapshot(
            total_packets=10,
            investigated_packets=2,
            cloud_fallback_invocation_count=2,
            wall_time_seconds=(91.0, 93.0),
            handoff_tokens_estimates=(1300, 1400),
        ),
        budget=config.cloud_fallback.budget,
    )

    assert accepted["accepted"] is True
    assert accepted["blockers"] == []
    assert all(check["passed"] is True for check in accepted["checks"].values())

    assert rejected["accepted"] is False
    assert set(rejected["blockers"]) == {
        "cloud_fallback_rate_total_above_gate",
        "cloud_fallback_rate_investigated_above_gate",
        "cloud_fallback_wall_time_above_gate",
        "compressed_handoff_tokens_above_gate",
    }


def test_cloud_fallback_can_use_real_adapter_client_when_gate_ready() -> None:
    packet = _build_packet()
    decision, _, local_result = _build_local_investigation(packet)
    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    provider = CloudFallbackInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        client=CrashingCloudFallbackClient(),
        real_adapter_client=FakeRealCloudFallbackClient(),
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.neko.example/v1",
            "OPENAI_API_KEY": "secret-token",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-5.4-xhigh",
        },
    )

    result = provider.investigate(request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["investigator_tier"] == "cloud_fallback_investigator"
    assert result["model_provider"] == "openai"
    assert result["model_name"] == "gpt-5.4-xhigh"
    assert result["summary"]["suspected_primary_cause"] == "real adapter confirmed db timeout on order lookup"
    assert "cloud_fallback_real_adapter_runtime_invoked" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_target_model_provider=neko_api_openai" in result["analysis_updates"]["notes"]



def test_cloud_fallback_auto_builds_openai_responses_client_when_gate_ready(monkeypatch) -> None:
    import json as json_module

    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], headers: dict[str, str], timeout: float):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["payload"] = json
        return FakeOpenAIResponsesResponse(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json_module.dumps(
                                    {
                                        "severity_band": "P1",
                                        "recommended_action": "page_owner",
                                        "confidence": 0.9,
                                        "suspected_primary_cause": "neko real adapter confirmed db timeout on order lookup",
                                        "failure_chain_summary": "neko real adapter reviewed the bounded local handoff and confirmed db timeout on order lookup",
                                        "hypotheses": [
                                            {
                                                "hypothesis": "bounded neko review confirms the checkout timeout regression",
                                                "confidence": 0.9,
                                                "supporting_reason_codes": ["neko_real_adapter_runtime"],
                                            }
                                        ],
                                        "unknowns": ["bounded remote proof only; operator rollout remains gated"],
                                        "notes": ["cloud_fallback_neko_real_adapter_mapped"],
                                    }
                                ),
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("app.investigator.cloud_fallback_openai_responses.httpx.post", fake_post)

    packet = _build_packet()
    decision, _, local_result = _build_local_investigation(packet)
    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    provider = CloudFallbackInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.neko.example/v1",
            "OPENAI_API_KEY": "secret-token",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-5.4-xhigh",
        },
    )

    result = provider.investigate(request)

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert captured["url"] == "https://api.neko.example/v1/responses"
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret-token",
    }
    assert captured["timeout"] == 90.0
    assert isinstance(captured["payload"], dict)
    assert captured["payload"]["model"] == "gpt-5.4-xhigh"
    assert result["investigator_tier"] == "cloud_fallback_investigator"
    assert result["model_provider"] == "openai"
    assert result["model_name"] == "gpt-5.4-xhigh"
    assert result["summary"]["suspected_primary_cause"] == "neko real adapter confirmed db timeout on order lookup"
    assert "cloud_fallback_real_adapter_runtime_invoked" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_real_adapter_response_mapped" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_neko_real_adapter_mapped" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_target_model_provider=neko_api_openai" in result["analysis_updates"]["notes"]



def test_run_cloud_fallback_with_local_fallback_returns_local_result_when_cloud_client_fails() -> None:
    packet = _build_packet()
    decision, config, local_result = _build_local_investigation(packet)
    request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=REPO_ROOT / "configs" / "escalation.yaml",
    )
    provider = CloudFallbackInvestigator.from_config(
        REPO_ROOT / "configs" / "escalation.yaml",
        client=CrashingCloudFallbackClient(),
    )

    result, audit = run_cloud_fallback_with_local_fallback(
        request,
        provider=provider,
        wall_time_seconds=4.2,
    )

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert result["investigator_tier"] == "local_primary_investigator"
    assert result["summary"]["recommended_action"] == "send_to_human_review"
    assert result["analysis_updates"]["recommended_action_changed"] is True
    assert "cloud_fallback_unavailable" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_provider_mode=deterministic_smoke" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_current_smoke_model=cloud-fallback-smoke" in result["analysis_updates"]["notes"]
    assert "cloud_fallback_future_real_adapter=openai_responses_api" in result["analysis_updates"]["notes"]
    assert (
        "cloud_fallback_future_real_adapter_enabled_env="
        "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED"
    ) in result["analysis_updates"]["notes"]
    assert "fail_closed_to=send_to_human_review" in result["analysis_updates"]["notes"]
    assert any("vendor timeout during bounded cloud review" in item for item in result["unknowns"])
    assert result["compressed_handoff"]["handoff_tokens_estimate"] <= config.cloud_fallback.budget.max_handoff_tokens
    assert audit.fallback_used is True
    assert audit.result_investigator_tier == "local_primary_investigator"
    assert audit.failure_reason == "vendor timeout during bounded cloud review"

    report = render_alert_report(packet, decision, result)
    assert "investigation_stage: local_primary" in report
    assert "cloud fallback unavailable: vendor timeout during bounded cloud review" in report
    assert "immediate action: `send_to_human_review`" in report
