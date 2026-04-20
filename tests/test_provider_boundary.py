from __future__ import annotations

from pathlib import Path

from app.investigator.provider_boundary import load_provider_boundary_config, resolve_real_adapter_gate
from app.investigator.router import load_investigator_routing_config


REPO_ROOT = Path(__file__).resolve().parents[1]



def test_provider_boundary_config_freezes_smoke_boundary_and_real_adapter_contracts() -> None:
    boundary = load_provider_boundary_config(REPO_ROOT / "configs" / "provider-boundary.yaml")
    routing = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    assert boundary.local_primary.mode == "deterministic_smoke"
    assert boundary.local_primary.fail_closed_recommended_action == "send_to_human_review"
    assert boundary.local_primary.smoke.model_provider == "local_vllm"
    assert boundary.local_primary.smoke.model_name == "local-primary-smoke"
    assert boundary.local_primary.smoke.model_name == routing.local_primary.model_name
    assert boundary.local_primary.real_adapter.adapter == "local_vllm_openai_compat"
    assert boundary.local_primary.real_adapter.transport == "openai_compatible_http"
    assert boundary.local_primary.real_adapter.activation == "env_opt_in"
    assert boundary.local_primary.real_adapter.enabled_env == "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED"
    assert boundary.local_primary.real_adapter.endpoint_env == "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL"
    assert boundary.local_primary.real_adapter.api_key_env is None
    assert boundary.local_primary.real_adapter.model_env == "WARNING_AGENT_LOCAL_PRIMARY_MODEL"
    assert boundary.local_primary.real_adapter.timeout_seconds == 45

    assert boundary.cloud_fallback.mode == "deterministic_smoke"
    assert boundary.cloud_fallback.fail_closed_recommended_action == "send_to_human_review"
    assert boundary.cloud_fallback.smoke.model_provider == "openai"
    assert boundary.cloud_fallback.smoke.model_name == "cloud-fallback-smoke"
    assert boundary.cloud_fallback.smoke.model_name == routing.cloud_fallback.model_name
    assert boundary.cloud_fallback.real_adapter.adapter == "openai_responses_api"
    assert boundary.cloud_fallback.real_adapter.transport == "openai_responses_api"
    assert boundary.cloud_fallback.real_adapter.activation == "env_opt_in"
    assert boundary.cloud_fallback.real_adapter.enabled_env == "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED"
    assert boundary.cloud_fallback.real_adapter.endpoint_env == "OPENAI_BASE_URL"
    assert boundary.cloud_fallback.real_adapter.api_key_env == "OPENAI_API_KEY"
    assert boundary.cloud_fallback.real_adapter.model_env == "WARNING_AGENT_CLOUD_FALLBACK_MODEL"
    assert boundary.cloud_fallback.real_adapter.timeout_seconds == 90



def test_real_adapter_gate_requires_opt_in_and_required_env_contract() -> None:
    boundary = load_provider_boundary_config(REPO_ROOT / "configs" / "provider-boundary.yaml")

    local_smoke = resolve_real_adapter_gate(boundary.local_primary, env={})
    local_missing = resolve_real_adapter_gate(
        boundary.local_primary,
        env={"WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true"},
    )
    local_ready = resolve_real_adapter_gate(
        boundary.local_primary,
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000/",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "local-primary-real-v1",
        },
    )
    cloud_ready = resolve_real_adapter_gate(
        boundary.cloud_fallback,
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.openai.example/v1/",
            "OPENAI_API_KEY": "secret-token",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-4o-mini",
        },
    )

    assert local_smoke.state == "smoke_default"
    assert local_smoke.missing_env == ()

    assert local_missing.state == "missing_env"
    assert set(local_missing.missing_env) == {
        "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL",
        "WARNING_AGENT_LOCAL_PRIMARY_MODEL",
    }

    assert local_ready.state == "ready"
    assert local_ready.endpoint == "http://127.0.0.1:8000"
    assert local_ready.model_name == "local-primary-real-v1"

    assert cloud_ready.state == "ready"
    assert cloud_ready.endpoint == "https://api.openai.example/v1"
    assert cloud_ready.api_key == "secret-token"
    assert cloud_ready.model_name == "gpt-4o-mini"
