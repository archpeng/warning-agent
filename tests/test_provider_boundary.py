from __future__ import annotations

from pathlib import Path

from app.investigator.provider_boundary import load_provider_boundary_config, resolve_real_adapter_gate
from app.investigator.router import load_investigator_routing_config


REPO_ROOT = Path(__file__).resolve().parents[1]



def test_provider_boundary_config_freezes_model_role_split_and_real_adapter_contracts() -> None:
    boundary = load_provider_boundary_config(REPO_ROOT / "configs" / "provider-boundary.yaml")
    routing = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    assert routing.routing.allowed_provider_order == ("local_primary",)
    assert routing.routing.local_readiness_requirement == "resident_service"
    assert routing.routing.local_not_ready_policy == "fallback_or_queue"
    assert routing.routing.local_not_ready_fallback_provider == "cloud_fallback"
    assert routing.routing.local_not_ready_queue_policy == "wait_for_local_primary_recovery"
    assert routing.routing.local_degraded_policy == "fallback_or_queue"

    assert boundary.local_primary.mode == "deterministic_smoke"
    assert boundary.local_primary.fail_closed_recommended_action == "send_to_human_review"
    assert boundary.local_primary.smoke.model_provider == "local_vllm"
    assert boundary.local_primary.smoke.model_name == "local-primary-smoke"
    assert boundary.local_primary.smoke.model_name == routing.local_primary.model_name
    assert boundary.local_primary.operating_contract.provider_role == "primary_local_investigator"
    assert boundary.local_primary.operating_contract.target_model_provider == "gemma4"
    assert boundary.local_primary.operating_contract.target_model_name == "gemma4-26b"
    assert boundary.local_primary.operating_contract.target_model_provider == routing.local_primary.contract_target.model_provider
    assert boundary.local_primary.operating_contract.target_model_name == routing.local_primary.contract_target.model_name
    assert boundary.local_primary.operating_contract.service_mode == "resident_prewarm_on_boot"
    assert boundary.local_primary.operating_contract.invocation_scope == "needs_investigation_only"
    assert boundary.local_primary.operating_contract.readiness_source == "resident_service"
    assert boundary.local_primary.operating_contract.ready_action == "invoke_when_needed"
    assert boundary.local_primary.operating_contract.not_ready_action == "fallback_or_queue"
    assert boundary.local_primary.operating_contract.degraded_action == "fallback_or_queue"
    assert boundary.local_primary.operating_contract.fallback_provider == "cloud_fallback"
    assert boundary.local_primary.operating_contract.queue_policy == "wait_for_local_primary_recovery"
    assert boundary.local_primary.real_adapter.adapter == "local_vllm_openai_compat"
    assert boundary.local_primary.real_adapter.transport == "openai_compatible_http"
    assert boundary.local_primary.real_adapter.activation == "env_opt_in"
    assert boundary.local_primary.real_adapter.enabled_env == "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED"
    assert boundary.local_primary.real_adapter.endpoint_env == "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL"
    assert boundary.local_primary.real_adapter.api_key_env == "WARNING_AGENT_LOCAL_PRIMARY_API_KEY"
    assert boundary.local_primary.real_adapter.api_key_mode == "optional"
    assert boundary.local_primary.real_adapter.model_env == "WARNING_AGENT_LOCAL_PRIMARY_MODEL"
    assert boundary.local_primary.real_adapter.timeout_seconds == 45

    assert boundary.cloud_fallback.mode == "deterministic_smoke"
    assert boundary.cloud_fallback.fail_closed_recommended_action == "send_to_human_review"
    assert boundary.cloud_fallback.smoke.model_provider == "openai"
    assert boundary.cloud_fallback.smoke.model_name == "cloud-fallback-smoke"
    assert boundary.cloud_fallback.smoke.model_name == routing.cloud_fallback.model_name
    assert boundary.cloud_fallback.operating_contract.provider_role == "sparse_cloud_fallback"
    assert boundary.cloud_fallback.operating_contract.target_model_provider == "neko_api_openai"
    assert boundary.cloud_fallback.operating_contract.target_model_name == "gpt-5.4-xhigh"
    assert boundary.cloud_fallback.operating_contract.target_model_provider == routing.cloud_fallback.contract_target.model_provider
    assert boundary.cloud_fallback.operating_contract.target_model_name == routing.cloud_fallback.contract_target.model_name
    assert boundary.cloud_fallback.operating_contract.service_mode == "env_gated_remote"
    assert boundary.cloud_fallback.operating_contract.invocation_scope == "fallback_only"
    assert boundary.cloud_fallback.operating_contract.readiness_source == "env_gate"
    assert boundary.cloud_fallback.operating_contract.ready_action == "invoke_when_selected"
    assert boundary.cloud_fallback.operating_contract.not_ready_action == "fail_closed"
    assert boundary.cloud_fallback.operating_contract.degraded_action == "fail_closed"
    assert boundary.cloud_fallback.operating_contract.fallback_provider is None
    assert boundary.cloud_fallback.operating_contract.queue_policy is None
    assert boundary.cloud_fallback.real_adapter.adapter == "openai_responses_api"
    assert boundary.cloud_fallback.real_adapter.transport == "openai_responses_api"
    assert boundary.cloud_fallback.real_adapter.activation == "env_opt_in"
    assert boundary.cloud_fallback.real_adapter.enabled_env == "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED"
    assert boundary.cloud_fallback.real_adapter.endpoint_env == "OPENAI_BASE_URL"
    assert boundary.cloud_fallback.real_adapter.api_key_env == "OPENAI_API_KEY"
    assert boundary.cloud_fallback.real_adapter.api_key_mode == "required"
    assert boundary.cloud_fallback.real_adapter.model_env == "WARNING_AGENT_CLOUD_FALLBACK_MODEL"
    assert boundary.cloud_fallback.real_adapter.timeout_seconds == 90



def test_real_adapter_gate_requires_opt_in_and_honors_optional_local_api_key_contract() -> None:
    boundary = load_provider_boundary_config(REPO_ROOT / "configs" / "provider-boundary.yaml")

    local_smoke = resolve_real_adapter_gate(boundary.local_primary, env={})
    local_missing = resolve_real_adapter_gate(
        boundary.local_primary,
        env={"WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true"},
    )
    local_ready_without_key = resolve_real_adapter_gate(
        boundary.local_primary,
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000/",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "local-primary-real-v1",
        },
    )
    local_ready_with_key = resolve_real_adapter_gate(
        boundary.local_primary,
        env={
            "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED": "true",
            "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL": "http://127.0.0.1:8000/",
            "WARNING_AGENT_LOCAL_PRIMARY_API_KEY": "local-secret",
            "WARNING_AGENT_LOCAL_PRIMARY_MODEL": "local-primary-real-v1",
        },
    )
    cloud_missing_key = resolve_real_adapter_gate(
        boundary.cloud_fallback,
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.openai.example/v1/",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-5.4-xhigh",
        },
    )
    cloud_ready = resolve_real_adapter_gate(
        boundary.cloud_fallback,
        env={
            "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED": "true",
            "OPENAI_BASE_URL": "https://api.openai.example/v1/",
            "OPENAI_API_KEY": "secret-token",
            "WARNING_AGENT_CLOUD_FALLBACK_MODEL": "gpt-5.4-xhigh",
        },
    )

    assert local_smoke.state == "smoke_default"
    assert local_smoke.api_key_env == "WARNING_AGENT_LOCAL_PRIMARY_API_KEY"
    assert local_smoke.api_key_mode == "optional"
    assert local_smoke.missing_env == ()

    assert local_missing.state == "missing_env"
    assert set(local_missing.missing_env) == {
        "WARNING_AGENT_LOCAL_PRIMARY_BASE_URL",
        "WARNING_AGENT_LOCAL_PRIMARY_MODEL",
    }

    assert local_ready_without_key.state == "ready"
    assert local_ready_without_key.endpoint == "http://127.0.0.1:8000"
    assert local_ready_without_key.api_key is None
    assert local_ready_without_key.api_key_env == "WARNING_AGENT_LOCAL_PRIMARY_API_KEY"
    assert local_ready_without_key.api_key_mode == "optional"
    assert local_ready_without_key.model_name == "local-primary-real-v1"

    assert local_ready_with_key.state == "ready"
    assert local_ready_with_key.api_key == "local-secret"

    assert cloud_missing_key.state == "missing_env"
    assert cloud_missing_key.api_key_env == "OPENAI_API_KEY"
    assert cloud_missing_key.api_key_mode == "required"
    assert cloud_missing_key.missing_env == ("OPENAI_API_KEY",)

    assert cloud_ready.state == "ready"
    assert cloud_ready.endpoint == "https://api.openai.example/v1"
    assert cloud_ready.api_key == "secret-token"
    assert cloud_ready.model_name == "gpt-5.4-xhigh"
