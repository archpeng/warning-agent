"""Provider boundary configuration and env-gated real-adapter resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

import yaml

from app.investigator.contracts import RecommendedAction

ProviderMode = Literal["deterministic_smoke"]
ProviderTransport = Literal["openai_compatible_http", "openai_responses_api"]
AdapterActivation = Literal["env_opt_in"]
RealAdapterGateState = Literal["smoke_default", "missing_env", "ready"]


@dataclass(frozen=True)
class SmokeProviderContract:
    model_provider: str
    model_name: str


@dataclass(frozen=True)
class RealProviderAdapterContract:
    adapter: str
    transport: ProviderTransport
    activation: AdapterActivation
    enabled_env: str
    endpoint_env: str
    api_key_env: str | None
    model_env: str
    timeout_seconds: int


@dataclass(frozen=True)
class ProviderBoundary:
    mode: ProviderMode
    fail_closed_recommended_action: RecommendedAction
    smoke: SmokeProviderContract
    real_adapter: RealProviderAdapterContract


@dataclass(frozen=True)
class ProviderBoundaryConfig:
    local_primary: ProviderBoundary
    cloud_fallback: ProviderBoundary


@dataclass(frozen=True)
class ResolvedRealAdapterGate:
    state: RealAdapterGateState
    adapter: str
    transport: ProviderTransport
    enabled_env: str
    endpoint: str | None
    api_key: str | None
    model_name: str | None
    missing_env: tuple[str, ...]


_ALLOWED_MODES = {"deterministic_smoke"}
_ALLOWED_TRANSPORTS = {"openai_compatible_http", "openai_responses_api"}
_ALLOWED_ACTIVATIONS = {"env_opt_in"}
_ENABLED_VALUES = {"1", "true", "yes", "on", "enabled"}


def _expect_mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _expect_non_empty_str(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _optional_non_empty_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional string field must be a string when present")
    normalized = value.strip()
    return normalized or None


def _expect_positive_int(value: object, *, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _load_smoke_contract(boundary_payload: dict[str, object], *, key: str) -> SmokeProviderContract:
    smoke_payload = _expect_mapping(boundary_payload.get("smoke") or {}, label=f"{key}.smoke")
    return SmokeProviderContract(
        model_provider=_expect_non_empty_str(
            smoke_payload.get("model_provider"),
            label=f"{key}.smoke.model_provider",
        ),
        model_name=_expect_non_empty_str(
            smoke_payload.get("model_name"),
            label=f"{key}.smoke.model_name",
        ),
    )


def _load_real_adapter(boundary_payload: dict[str, object], *, key: str) -> RealProviderAdapterContract:
    adapter_payload = _expect_mapping(
        boundary_payload.get("real_adapter") or {},
        label=f"{key}.real_adapter",
    )
    transport = _expect_non_empty_str(
        adapter_payload.get("transport"),
        label=f"{key}.real_adapter.transport",
    )
    activation = _expect_non_empty_str(
        adapter_payload.get("activation"),
        label=f"{key}.real_adapter.activation",
    )
    if transport not in _ALLOWED_TRANSPORTS:
        raise ValueError(f"{key}.real_adapter.transport is unsupported: {transport}")
    if activation not in _ALLOWED_ACTIVATIONS:
        raise ValueError(f"{key}.real_adapter.activation is unsupported: {activation}")

    return RealProviderAdapterContract(
        adapter=_expect_non_empty_str(
            adapter_payload.get("adapter"),
            label=f"{key}.real_adapter.adapter",
        ),
        transport=transport,
        activation=activation,
        enabled_env=_expect_non_empty_str(
            adapter_payload.get("enabled_env"),
            label=f"{key}.real_adapter.enabled_env",
        ),
        endpoint_env=_expect_non_empty_str(
            adapter_payload.get("endpoint_env"),
            label=f"{key}.real_adapter.endpoint_env",
        ),
        api_key_env=_optional_non_empty_str(adapter_payload.get("api_key_env")),
        model_env=_expect_non_empty_str(
            adapter_payload.get("model_env"),
            label=f"{key}.real_adapter.model_env",
        ),
        timeout_seconds=_expect_positive_int(
            adapter_payload.get("timeout_seconds"),
            label=f"{key}.real_adapter.timeout_seconds",
        ),
    )


def _load_boundary(payload: dict[str, object], key: str) -> ProviderBoundary:
    boundary_payload = _expect_mapping(payload.get(key) or {}, label=key)
    mode = _expect_non_empty_str(boundary_payload.get("mode"), label=f"{key}.mode")
    if mode not in _ALLOWED_MODES:
        raise ValueError(f"{key}.mode is unsupported: {mode}")

    return ProviderBoundary(
        mode=mode,
        fail_closed_recommended_action=_expect_non_empty_str(
            boundary_payload.get("fail_closed_recommended_action"),
            label=f"{key}.fail_closed_recommended_action",
        ),
        smoke=_load_smoke_contract(boundary_payload, key=key),
        real_adapter=_load_real_adapter(boundary_payload, key=key),
    )


def _read_env_value(env: Mapping[str, str | None], key: str | None) -> str | None:
    if not key:
        return None
    value = env.get(key)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _env_enabled(env: Mapping[str, str | None], key: str) -> bool:
    value = _read_env_value(env, key)
    return value is not None and value.lower() in _ENABLED_VALUES


def resolve_real_adapter_gate(
    boundary: ProviderBoundary,
    env: Mapping[str, str | None] = os.environ,
) -> ResolvedRealAdapterGate:
    adapter = boundary.real_adapter
    if not _env_enabled(env, adapter.enabled_env):
        return ResolvedRealAdapterGate(
            state="smoke_default",
            adapter=adapter.adapter,
            transport=adapter.transport,
            enabled_env=adapter.enabled_env,
            endpoint=None,
            api_key=None,
            model_name=None,
            missing_env=(),
        )

    endpoint = _read_env_value(env, adapter.endpoint_env)
    if endpoint is not None:
        endpoint = endpoint.rstrip("/")
    api_key = _read_env_value(env, adapter.api_key_env)
    model_name = _read_env_value(env, adapter.model_env)

    missing_env: list[str] = []
    if endpoint is None:
        missing_env.append(adapter.endpoint_env)
    if adapter.api_key_env and api_key is None:
        missing_env.append(adapter.api_key_env)
    if model_name is None:
        missing_env.append(adapter.model_env)

    state: RealAdapterGateState = "ready" if not missing_env else "missing_env"
    return ResolvedRealAdapterGate(
        state=state,
        adapter=adapter.adapter,
        transport=adapter.transport,
        enabled_env=adapter.enabled_env,
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
        missing_env=tuple(missing_env),
    )


def load_provider_boundary_config(
    config_path: str | Path = Path("configs/provider-boundary.yaml"),
) -> ProviderBoundaryConfig:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider boundary config must be a mapping")
    return ProviderBoundaryConfig(
        local_primary=_load_boundary(payload, "local_primary"),
        cloud_fallback=_load_boundary(payload, "cloud_fallback"),
    )
