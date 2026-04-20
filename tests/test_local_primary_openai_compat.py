from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.local_primary_openai_compat import LocalPrimaryOpenAICompatibleProvider
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"


class FakeResponse:
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



def _build_request():
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    packet = build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))
    decision = _load_json(DECISION_FIXTURE)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")
    plan = plan_investigation(packet, decision, config=config)
    assert plan.request is not None
    return plan.request



def test_local_primary_openai_compat_provider_maps_fake_response_to_schema_valid_result(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], headers: dict[str, str], timeout: float):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "summary": {
                                        "severity_band": "P1",
                                        "recommended_action": "page_owner",
                                        "confidence": 0.89,
                                        "reason_codes": ["error_rate_spike", "local_primary_real_adapter"],
                                        "suspected_primary_cause": "payment gateway timeout saturation",
                                        "failure_chain_summary": "local-primary real adapter linked payment gateway timeout saturation to checkout POST /api/pay.",
                                    },
                                    "hypotheses": [
                                        {
                                            "hypothesis": "payment gateway timeout saturation is driving checkout POST /api/pay failures",
                                            "confidence": 0.89,
                                            "supporting_reason_codes": ["error_rate_spike", "local_primary_real_adapter"],
                                        }
                                    ],
                                    "routing": {
                                        "owner_hint": "payments-oncall",
                                        "repo_candidates": ["checkout-service", "payment-gateway-client"],
                                        "suspected_code_paths": [
                                            "services/checkout/post_api_pay.py",
                                            "repos/payment-gateway-client/post_api_pay",
                                        ],
                                        "escalation_target": "payments-oncall",
                                    },
                                    "evidence_refs": {
                                        "prometheus_ref_ids": ["prom://query/high_error_rate_window_300s"],
                                        "signoz_ref_ids": ["signoz://trace/query-123", "signoz://logs/query-456"],
                                        "trace_ids": ["7f8a3c", "7f8a40"],
                                        "code_refs": ["services/checkout/post_api_pay.py"],
                                    },
                                    "unknowns": ["live endpoint was not used in unit test"],
                                    "analysis_updates": {
                                        "notes": ["local_primary_openai_compat_unit_test"],
                                        "severity_band_changed": False,
                                        "recommended_action_changed": False,
                                        "fallback_invocation_was_correct": None,
                                    },
                                }
                            )
                        }
                    }
                ]
            }
        )

    import json as json_module

    monkeypatch.setattr("app.investigator.local_primary_openai_compat.httpx.post", fake_post)
    provider = LocalPrimaryOpenAICompatibleProvider(
        endpoint="http://127.0.0.1:8000/v1",
        model_name="minimax-m2.7-highspeed",
        timeout_seconds=45,
    )

    result = provider.investigate(_build_request())

    validator = Draft202012Validator(load_investigation_schema())
    errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)

    assert not errors
    assert captured["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert captured["timeout"] == 45.0
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert captured["json"]["model"] == "minimax-m2.7-highspeed"
    assert result["model_provider"] == "local_vllm"
    assert result["model_name"] == "minimax-m2.7-highspeed"
    assert result["summary"]["suspected_primary_cause"] == "payment gateway timeout saturation"
    assert "local_primary_openai_compat_unit_test" in result["analysis_updates"]["notes"]
    assert "local_primary_real_adapter_response_mapped" in result["analysis_updates"]["notes"]
    assert result["hypotheses"][0]["rank"] == 1



def test_local_primary_openai_compat_provider_sends_optional_api_key_when_present(monkeypatch) -> None:
    captured_headers: dict[str, str] = {}
    import json as json_module

    def fake_post(url: str, *, json: dict[str, object], headers: dict[str, str], timeout: float):
        captured_headers.update(headers)
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "summary": {
                                        "suspected_primary_cause": "payment gateway timeout saturation",
                                        "failure_chain_summary": "bounded local-primary request remained scoped",
                                    },
                                    "hypotheses": [
                                        {
                                            "hypothesis": "payment gateway timeout saturation is driving the incident",
                                            "confidence": 0.73,
                                            "supporting_reason_codes": ["local_primary_real_adapter"],
                                        }
                                    ],
                                    "unknowns": ["optional API key header path exercised"],
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.investigator.local_primary_openai_compat.httpx.post", fake_post)
    provider = LocalPrimaryOpenAICompatibleProvider(
        endpoint="http://127.0.0.1:8000/v1",
        model_name="minimax-m2.7-highspeed",
        timeout_seconds=45,
        api_key="local-secret",
    )

    result = provider.investigate(_build_request())

    assert captured_headers["Content-Type"] == "application/json"
    assert captured_headers["Authorization"] == "Bearer local-secret"
    assert result["summary"]["investigation_used"] is True
    assert result["unknowns"] == ["optional API key header path exercised"]
