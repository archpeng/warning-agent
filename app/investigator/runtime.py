"""Bounded local-first investigation execution path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Literal, Protocol

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.cloud_fallback import (
    CloudFallbackAuditRecord,
    CloudFallbackInvestigator,
    build_cloud_fallback_request,
    run_cloud_fallback_with_local_fallback,
)
from app.investigator.contracts import InvestigationResult
from app.investigator.fallback import build_degraded_local_fallback, run_local_primary_with_fallback
from app.investigator.local_primary import (
    LocalPrimaryAbnormalPathDecision,
    LocalPrimaryInvestigator,
    LocalPrimaryResidentLifecycle,
    decide_local_primary_abnormal_path,
)
from app.investigator.provider_boundary import load_provider_boundary_config
from app.investigator.router import (
    CloudFallbackRoutePlan,
    InvestigationRoutePlan,
    load_investigator_routing_config,
    plan_cloud_fallback,
    plan_investigation,
)
from app.packet.contracts import IncidentPacket


class LocalPrimaryProviderProtocol(Protocol):
    def investigate(self, request: object) -> InvestigationResult:
        ...


class CloudFallbackProviderProtocol(Protocol):
    def investigate(self, request: object) -> InvestigationResult:
        ...


RuntimeExecutionContext = Literal["direct_runtime", "warning_worker"]


@dataclass(frozen=True)
class LocalPrimaryRecoveryWaitSignal:
    resident_lifecycle: LocalPrimaryResidentLifecycle
    abnormal_path: LocalPrimaryAbnormalPathDecision


class LocalPrimaryRecoveryRequired(RuntimeError):
    def __init__(self, signal: LocalPrimaryRecoveryWaitSignal) -> None:
        self.signal = signal
        super().__init__(signal.abnormal_path.reason)


@dataclass(frozen=True)
class InvestigationExecutionTrace:
    route_plan: InvestigationRoutePlan
    local_result: InvestigationResult | None
    cloud_plan: CloudFallbackRoutePlan | None
    cloud_audit: CloudFallbackAuditRecord | None
    final_result: InvestigationResult | None


def _resolve_local_abnormal_path(
    provider: LocalPrimaryProviderProtocol,
    *,
    runtime_context: RuntimeExecutionContext,
) -> tuple[LocalPrimaryResidentLifecycle, LocalPrimaryAbnormalPathDecision] | None:
    lifecycle = getattr(provider, "resident_lifecycle", None)
    if not isinstance(lifecycle, LocalPrimaryResidentLifecycle):
        return None
    if lifecycle.state == "ready":
        return None

    boundary = load_provider_boundary_config().local_primary
    abnormal_path = decide_local_primary_abnormal_path(
        lifecycle,
        runtime_context=runtime_context,
        fallback_provider=boundary.operating_contract.fallback_provider,
        queue_policy=boundary.operating_contract.queue_policy,
    )
    return lifecycle, abnormal_path



def run_investigation_runtime(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    config_path: str | Path = Path("configs/escalation.yaml"),
    repo_root: str | Path = Path("."),
    local_provider: LocalPrimaryProviderProtocol | None = None,
    cloud_provider: CloudFallbackProviderProtocol | None = None,
    runtime_context: RuntimeExecutionContext = "direct_runtime",
) -> InvestigationExecutionTrace:
    config = load_investigator_routing_config(config_path)
    route_plan = plan_investigation(packet, decision, config=config)
    if not route_plan.should_investigate or route_plan.request is None:
        return InvestigationExecutionTrace(
            route_plan=route_plan,
            local_result=None,
            cloud_plan=None,
            cloud_audit=None,
            final_result=None,
        )

    local_provider = local_provider or LocalPrimaryInvestigator.from_config(
        config_path,
        repo_root=repo_root,
    )
    local_abnormal_path = _resolve_local_abnormal_path(local_provider, runtime_context=runtime_context)
    if local_abnormal_path is not None:
        resident_lifecycle, abnormal_path = local_abnormal_path
        if abnormal_path.action == "queue_wait_for_local_primary_recovery":
            raise LocalPrimaryRecoveryRequired(
                LocalPrimaryRecoveryWaitSignal(
                    resident_lifecycle=resident_lifecycle,
                    abnormal_path=abnormal_path,
                )
            )
        local_result = build_degraded_local_fallback(
            packet,
            decision,
            failure_reason=abnormal_path.reason,
            resident_lifecycle=resident_lifecycle,
            abnormal_path=abnormal_path,
        )
        cloud_plan = CloudFallbackRoutePlan(
            should_escalate=True,
            trigger_reasons=(f"local_primary_{resident_lifecycle.state}_fallback_to_cloud",),
        )
    else:
        local_result = run_local_primary_with_fallback(
            packet,
            decision,
            route_plan.request,
            provider=local_provider,
        )
        cloud_plan = plan_cloud_fallback(local_result, config=config)
    if not cloud_plan.should_escalate:
        return InvestigationExecutionTrace(
            route_plan=route_plan,
            local_result=local_result,
            cloud_plan=cloud_plan,
            cloud_audit=None,
            final_result=local_result,
        )

    cloud_provider = cloud_provider or CloudFallbackInvestigator.from_config(config_path)
    cloud_request = build_cloud_fallback_request(
        packet,
        decision,
        local_result,
        config_path=config_path,
    )
    started_at = time.perf_counter()
    final_result, cloud_audit = run_cloud_fallback_with_local_fallback(
        cloud_request,
        provider=cloud_provider,
        wall_time_seconds=time.perf_counter() - started_at,
    )
    return InvestigationExecutionTrace(
        route_plan=route_plan,
        local_result=local_result,
        cloud_plan=cloud_plan,
        cloud_audit=cloud_audit,
        final_result=final_result,
    )
