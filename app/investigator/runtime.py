"""Bounded local-first investigation execution path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Protocol

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.cloud_fallback import (
    CloudFallbackAuditRecord,
    CloudFallbackInvestigator,
    build_cloud_fallback_request,
    run_cloud_fallback_with_local_fallback,
)
from app.investigator.contracts import InvestigationResult
from app.investigator.fallback import run_local_primary_with_fallback
from app.investigator.local_primary import LocalPrimaryInvestigator
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


@dataclass(frozen=True)
class InvestigationExecutionTrace:
    route_plan: InvestigationRoutePlan
    local_result: InvestigationResult | None
    cloud_plan: CloudFallbackRoutePlan | None
    cloud_audit: CloudFallbackAuditRecord | None
    final_result: InvestigationResult | None


def run_investigation_runtime(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    config_path: str | Path = Path("configs/escalation.yaml"),
    repo_root: str | Path = Path("."),
    local_provider: LocalPrimaryProviderProtocol | None = None,
    cloud_provider: CloudFallbackProviderProtocol | None = None,
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
