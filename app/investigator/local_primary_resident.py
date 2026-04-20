"""Resident lifecycle and abnormal-path helpers for local-primary investigation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Mapping, Protocol

from app.investigator.provider_boundary import (
    ProviderBoundary,
    ResolvedRealAdapterGate,
    load_provider_boundary_config,
    resolve_real_adapter_gate,
)
from app.investigator.router import load_investigator_routing_config


class RealAdapterProviderProtocol(Protocol):
    def investigate(self, request: object) -> object:
        ...


LocalPrimaryResidentState = Literal["ready", "not_ready", "degraded"]
LocalPrimaryResidentProviderMode = Literal["smoke_resident", "real_adapter_resident"]
LocalPrimaryPrewarmSource = Literal["fastapi_startup", "runtime_entry_boot", "live_smoke_boot", "provider_init"]
LocalPrimaryRuntimeContext = Literal["direct_runtime", "warning_worker"]
LocalPrimaryAbnormalAction = Literal["fallback_to_cloud_fallback", "queue_wait_for_local_primary_recovery"]
ProviderBuilder = Callable[[ProviderBoundary, ResolvedRealAdapterGate, str], RealAdapterProviderProtocol]


@dataclass(frozen=True)
class LocalPrimaryResidentLifecycle:
    service_mode: str
    invocation_scope: str
    startup_cost_policy: str
    provider_mode: LocalPrimaryResidentProviderMode
    state: LocalPrimaryResidentState
    gate_state: str
    model_name: str
    prewarm_completed_once: bool
    prewarm_attempt_count: int
    prewarm_source: LocalPrimaryPrewarmSource
    reason: str | None = None


@dataclass(frozen=True)
class LocalPrimaryResidentResolution:
    lifecycle: LocalPrimaryResidentLifecycle
    real_adapter_provider: RealAdapterProviderProtocol | None = None


@dataclass(frozen=True)
class LocalPrimaryAbnormalPathDecision:
    runtime_context: LocalPrimaryRuntimeContext
    lifecycle_state: LocalPrimaryResidentState
    gate_state: str
    action: LocalPrimaryAbnormalAction
    fallback_provider: str | None
    queue_policy: str | None
    reason: str


@dataclass
class _LocalPrimaryResidentCache:
    signature: tuple[str, ...]
    resolution: LocalPrimaryResidentResolution


_LOCAL_PRIMARY_RESIDENT_CACHE: _LocalPrimaryResidentCache | None = None



def _local_primary_cache_signature(
    *,
    boundary: ProviderBoundary,
    gate: ResolvedRealAdapterGate,
) -> tuple[str, ...]:
    return (
        boundary.mode,
        boundary.smoke.model_name,
        boundary.operating_contract.service_mode,
        boundary.operating_contract.invocation_scope,
        gate.state,
        gate.endpoint or "",
        gate.model_name or "",
    )



def reset_local_primary_resident_service() -> None:
    global _LOCAL_PRIMARY_RESIDENT_CACHE
    _LOCAL_PRIMARY_RESIDENT_CACHE = None



def _build_local_primary_resident_resolution(
    *,
    boundary: ProviderBoundary,
    gate: ResolvedRealAdapterGate,
    budget_startup_cost_policy: str,
    model_provider: str,
    prewarm_source: LocalPrimaryPrewarmSource,
    real_adapter_provider: RealAdapterProviderProtocol | None,
    build_real_provider: ProviderBuilder,
) -> LocalPrimaryResidentResolution:
    if gate.state == "smoke_default":
        return LocalPrimaryResidentResolution(
            lifecycle=LocalPrimaryResidentLifecycle(
                service_mode=boundary.operating_contract.service_mode,
                invocation_scope=boundary.operating_contract.invocation_scope,
                startup_cost_policy=budget_startup_cost_policy,
                provider_mode="smoke_resident",
                state="ready",
                gate_state=gate.state,
                model_name=boundary.smoke.model_name,
                prewarm_completed_once=True,
                prewarm_attempt_count=1,
                prewarm_source=prewarm_source,
                reason="smoke-default resident local-primary requires no external warmup",
            ),
            real_adapter_provider=None,
        )

    if gate.state == "missing_env":
        missing_env = ", ".join(gate.missing_env)
        return LocalPrimaryResidentResolution(
            lifecycle=LocalPrimaryResidentLifecycle(
                service_mode=boundary.operating_contract.service_mode,
                invocation_scope=boundary.operating_contract.invocation_scope,
                startup_cost_policy=budget_startup_cost_policy,
                provider_mode="real_adapter_resident",
                state="not_ready",
                gate_state=gate.state,
                model_name=boundary.operating_contract.target_model_name,
                prewarm_completed_once=True,
                prewarm_attempt_count=1,
                prewarm_source=prewarm_source,
                reason=f"local_primary real adapter gate enabled but missing env: {missing_env}",
            ),
            real_adapter_provider=None,
        )

    try:
        provider = real_adapter_provider or build_real_provider(boundary, gate, model_provider)
    except Exception as exc:
        return LocalPrimaryResidentResolution(
            lifecycle=LocalPrimaryResidentLifecycle(
                service_mode=boundary.operating_contract.service_mode,
                invocation_scope=boundary.operating_contract.invocation_scope,
                startup_cost_policy=budget_startup_cost_policy,
                provider_mode="real_adapter_resident",
                state="degraded",
                gate_state=gate.state,
                model_name=gate.model_name or boundary.operating_contract.target_model_name,
                prewarm_completed_once=True,
                prewarm_attempt_count=1,
                prewarm_source=prewarm_source,
                reason=f"local_primary resident prewarm failed: {exc}",
            ),
            real_adapter_provider=None,
        )

    return LocalPrimaryResidentResolution(
        lifecycle=LocalPrimaryResidentLifecycle(
            service_mode=boundary.operating_contract.service_mode,
            invocation_scope=boundary.operating_contract.invocation_scope,
            startup_cost_policy=budget_startup_cost_policy,
            provider_mode="real_adapter_resident",
            state="ready",
            gate_state=gate.state,
            model_name=gate.model_name or boundary.operating_contract.target_model_name,
            prewarm_completed_once=True,
            prewarm_attempt_count=1,
            prewarm_source=prewarm_source,
            reason="resident real adapter provider materialized",
        ),
        real_adapter_provider=provider,
    )



def local_primary_resident_lifecycle_payload(
    lifecycle: LocalPrimaryResidentLifecycle,
) -> dict[str, object]:
    return {
        "service_mode": lifecycle.service_mode,
        "invocation_scope": lifecycle.invocation_scope,
        "startup_cost_policy": lifecycle.startup_cost_policy,
        "provider_mode": lifecycle.provider_mode,
        "state": lifecycle.state,
        "gate_state": lifecycle.gate_state,
        "model_name": lifecycle.model_name,
        "prewarm_completed_once": lifecycle.prewarm_completed_once,
        "prewarm_attempt_count": lifecycle.prewarm_attempt_count,
        "prewarm_source": lifecycle.prewarm_source,
        "reason": lifecycle.reason,
    }



def decide_local_primary_abnormal_path(
    lifecycle: LocalPrimaryResidentLifecycle,
    *,
    runtime_context: LocalPrimaryRuntimeContext,
    fallback_provider: str | None,
    queue_policy: str | None,
) -> LocalPrimaryAbnormalPathDecision:
    if lifecycle.state == "ready":
        raise ValueError("ready lifecycle does not require abnormal-path routing")

    reason = lifecycle.reason or f"local_primary resident service {lifecycle.state}"
    if runtime_context == "warning_worker" and lifecycle.state == "degraded" and lifecycle.gate_state == "ready":
        return LocalPrimaryAbnormalPathDecision(
            runtime_context=runtime_context,
            lifecycle_state=lifecycle.state,
            gate_state=lifecycle.gate_state,
            action="queue_wait_for_local_primary_recovery",
            fallback_provider=fallback_provider,
            queue_policy=queue_policy,
            reason=reason,
        )

    return LocalPrimaryAbnormalPathDecision(
        runtime_context=runtime_context,
        lifecycle_state=lifecycle.state,
        gate_state=lifecycle.gate_state,
        action="fallback_to_cloud_fallback",
        fallback_provider=fallback_provider,
        queue_policy=queue_policy,
        reason=reason,
    )



def local_primary_abnormal_path_payload(
    decision: LocalPrimaryAbnormalPathDecision,
) -> dict[str, object]:
    return {
        "runtime_context": decision.runtime_context,
        "lifecycle_state": decision.lifecycle_state,
        "gate_state": decision.gate_state,
        "action": decision.action,
        "fallback_provider": decision.fallback_provider,
        "queue_policy": decision.queue_policy,
        "reason": decision.reason,
    }



def prewarm_local_primary_resident_service(
    *,
    config_path: str | Path = Path("configs/escalation.yaml"),
    repo_root: str | Path = Path("."),
    env: Mapping[str, str | None] = os.environ,
    prewarm_source: LocalPrimaryPrewarmSource = "provider_init",
    real_adapter_provider: RealAdapterProviderProtocol | None = None,
    build_real_provider: ProviderBuilder,
) -> LocalPrimaryResidentResolution:
    global _LOCAL_PRIMARY_RESIDENT_CACHE

    repo_root = Path(repo_root)
    config = load_investigator_routing_config(config_path)
    boundary = load_provider_boundary_config(repo_root / "configs" / "provider-boundary.yaml").local_primary
    gate = resolve_real_adapter_gate(boundary, env=env)
    signature = _local_primary_cache_signature(boundary=boundary, gate=gate)

    if _LOCAL_PRIMARY_RESIDENT_CACHE is not None and _LOCAL_PRIMARY_RESIDENT_CACHE.signature == signature:
        cached = _LOCAL_PRIMARY_RESIDENT_CACHE.resolution
        if real_adapter_provider is not None and cached.real_adapter_provider is None and gate.state == "ready":
            updated = LocalPrimaryResidentResolution(
                lifecycle=cached.lifecycle,
                real_adapter_provider=real_adapter_provider,
            )
            _LOCAL_PRIMARY_RESIDENT_CACHE = _LocalPrimaryResidentCache(signature=signature, resolution=updated)
            return updated
        return cached

    resolution = _build_local_primary_resident_resolution(
        boundary=boundary,
        gate=gate,
        budget_startup_cost_policy=config.local_primary.budget_contract.startup_cost_policy,
        model_provider=config.local_primary.model_provider,
        prewarm_source=prewarm_source,
        real_adapter_provider=real_adapter_provider,
        build_real_provider=build_real_provider,
    )
    _LOCAL_PRIMARY_RESIDENT_CACHE = _LocalPrimaryResidentCache(signature=signature, resolution=resolution)
    return resolution
