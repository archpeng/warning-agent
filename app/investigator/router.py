"""Local-first investigator routing contract and config loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.base import (
    InvestigationRequest,
    InvestigatorBudget,
    InvestigatorMode,
    ProviderName,
    build_investigation_request,
)
from app.investigator.contracts import InvestigationResult
from app.packet.contracts import IncidentPacket

CloudPhase = Literal["P5"]


@dataclass(frozen=True)
class RoutingPolicy:
    require_needs_investigation: bool
    allowed_provider_order: tuple[ProviderName, ...]
    allow_cloud_fallback: bool


@dataclass(frozen=True)
class LocalPrimaryConfig:
    enabled: bool
    model_provider: str
    model_name: str
    budget: InvestigatorBudget
    trigger_rules: dict[str, float]


@dataclass(frozen=True)
class CloudFallbackBudget:
    max_invocation_rate_total: float
    max_invocation_rate_investigated: float
    max_wall_time_seconds: int
    max_handoff_tokens: int


@dataclass(frozen=True)
class CloudFallbackAuditConfig:
    require_parent_investigation_id: bool
    require_handoff_markdown: bool
    require_handoff_tokens_estimate: bool
    require_failure_reason_note: bool


@dataclass(frozen=True)
class CloudFallbackConfig:
    enabled: bool
    available_phase: CloudPhase
    model_provider: str
    model_name: str
    budget: CloudFallbackBudget
    audit: CloudFallbackAuditConfig
    trigger_rules: dict[str, bool | float]


@dataclass(frozen=True)
class InvestigatorRoutingConfig:
    default_mode: InvestigatorMode
    routing: RoutingPolicy
    local_primary: LocalPrimaryConfig
    cloud_fallback: CloudFallbackConfig
    max_concurrent_local_primary: int
    max_concurrent_cloud_fallback: int


@dataclass(frozen=True)
class InvestigationRoutePlan:
    mode: InvestigatorMode
    should_investigate: bool
    selected_provider: ProviderName | None
    provider_order: tuple[ProviderName, ...]
    trigger_reasons: tuple[str, ...]
    allow_cloud_fallback: bool
    budget: InvestigatorBudget | None
    request: InvestigationRequest | None


@dataclass(frozen=True)
class CloudFallbackRoutePlan:
    should_escalate: bool
    trigger_reasons: tuple[str, ...]


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("investigator routing config must be a mapping")
    return payload


def load_investigator_routing_config(
    config_path: str | Path = Path("configs/escalation.yaml"),
) -> InvestigatorRoutingConfig:
    payload = _load_yaml(Path(config_path))
    investigator = payload["investigator"]
    routing = investigator["routing"]
    local_primary = investigator["local_primary"]
    cloud_fallback = investigator["cloud_fallback"]
    budget = local_primary["budgets"]
    cloud_budget = cloud_fallback["budgets"]
    cloud_audit = cloud_fallback["audit"]

    return InvestigatorRoutingConfig(
        default_mode=investigator["default_mode"],
        routing=RoutingPolicy(
            require_needs_investigation=bool(routing["require_needs_investigation"]),
            allowed_provider_order=tuple(routing["allowed_provider_order"]),
            allow_cloud_fallback=bool(routing["allow_cloud_fallback"]),
        ),
        local_primary=LocalPrimaryConfig(
            enabled=bool(local_primary["enabled"]),
            model_provider=str(local_primary["model_provider"]),
            model_name=str(local_primary["model_name"]),
            budget=InvestigatorBudget(
                wall_time_seconds=int(budget["wall_time_seconds"]),
                max_tool_calls=int(budget["max_tool_calls"]),
                max_prompt_tokens=int(budget["max_prompt_tokens"]),
                max_completion_tokens=int(budget["max_completion_tokens"]),
                max_retrieval_refs=int(budget["max_retrieval_refs"]),
                max_trace_refs=int(budget["max_trace_refs"]),
                max_log_refs=int(budget["max_log_refs"]),
                max_code_refs=int(budget["max_code_refs"]),
            ),
            trigger_rules={key: float(value) for key, value in local_primary["trigger_rules"].items()},
        ),
        cloud_fallback=CloudFallbackConfig(
            enabled=bool(cloud_fallback["enabled"]),
            available_phase=str(cloud_fallback["available_phase"]),
            model_provider=str(cloud_fallback["model_provider"]),
            model_name=str(cloud_fallback["model_name"]),
            budget=CloudFallbackBudget(
                max_invocation_rate_total=float(cloud_budget["max_invocation_rate_total"]),
                max_invocation_rate_investigated=float(cloud_budget["max_invocation_rate_investigated"]),
                max_wall_time_seconds=int(cloud_budget["max_wall_time_seconds"]),
                max_handoff_tokens=int(cloud_budget["max_handoff_tokens"]),
            ),
            audit=CloudFallbackAuditConfig(
                require_parent_investigation_id=bool(cloud_audit["require_parent_investigation_id"]),
                require_handoff_markdown=bool(cloud_audit["require_handoff_markdown"]),
                require_handoff_tokens_estimate=bool(cloud_audit["require_handoff_tokens_estimate"]),
                require_failure_reason_note=bool(cloud_audit["require_failure_reason_note"]),
            ),
            trigger_rules={key: value for key, value in cloud_fallback["trigger_rules"].items()},
        ),
        max_concurrent_local_primary=int(investigator["max_concurrent_local_primary"]),
        max_concurrent_cloud_fallback=int(investigator["max_concurrent_cloud_fallback"]),
    )


def _local_primary_route_reasons(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    config: InvestigatorRoutingConfig,
) -> tuple[str, ...]:
    rules = config.local_primary.trigger_rules
    reasons: list[str] = []
    decision_reasons = set(decision["investigation_trigger_reasons"])
    confidence = float(decision["confidence"])
    novelty_score = float(decision["novelty_score"])
    severity_score = float(decision["severity_score"])
    blast_radius_score = float(packet["topology"]["blast_radius_score"])

    if decision["analyzer_family"] == "hybrid":
        if (
            severity_score >= rules["severity_probability_at_or_above"]
            and blast_radius_score >= rules["blast_radius_at_or_above"]
        ):
            reasons.append("calibrated_severity_high_route_gate")
        if (
            "signoz_alert_firing" in decision["reason_codes"]
            and severity_score >= 0.5
            and blast_radius_score >= rules["blast_radius_at_or_above"]
        ):
            reasons.append("signoz_primary_route_gate")
        if (
            "signoz_alert_firing" in decision["reason_codes"]
            and severity_score >= 0.5
            and confidence < rules["confidence_below"]
        ):
            reasons.append("signoz_low_confidence_route_gate")
        if "retrieval_conflict" in decision_reasons:
            reasons.append("retrieval_conflict_route_gate")
        return tuple(reasons)

    if confidence < rules["confidence_below"]:
        reasons.append("confidence_below_route_gate")
    if "novelty_high" in decision_reasons and novelty_score >= rules["novelty_at_or_above"]:
        reasons.append("novelty_at_or_above_route_gate")
    if "blast_radius_high" in decision_reasons and blast_radius_score >= rules["blast_radius_at_or_above"]:
        reasons.append("blast_radius_at_or_above_route_gate")
    if "retrieval_conflict" in decision_reasons:
        reasons.append("retrieval_conflict_route_gate")
    if (
        decision["recommended_action"] == "page_owner"
        and confidence <= rules["page_owner_requires_confidence_below"]
    ):
        reasons.append("page_owner_low_confidence_route_gate")

    return tuple(reasons)


def _has_conflicting_hypotheses(result: InvestigationResult) -> bool:
    hypotheses = result.get("hypotheses") or []
    if len(hypotheses) < 2:
        return False

    top = hypotheses[0]
    runner_up = hypotheses[1]
    top_confidence = float(top["confidence"])
    runner_up_confidence = float(runner_up["confidence"])
    confidence_gap = abs(top_confidence - runner_up_confidence)

    return top_confidence >= 0.65 and runner_up_confidence >= 0.65 and confidence_gap <= 0.1



def plan_cloud_fallback(
    result: InvestigationResult,
    *,
    config: InvestigatorRoutingConfig,
) -> CloudFallbackRoutePlan:
    if not config.routing.allow_cloud_fallback or not config.cloud_fallback.enabled:
        return CloudFallbackRoutePlan(should_escalate=False, trigger_reasons=())

    rules = config.cloud_fallback.trigger_rules
    unknowns = result.get("unknowns") or []
    has_unknowns = bool(unknowns)
    if bool(rules.get("unresolved_unknowns_required", False)) and not has_unknowns:
        return CloudFallbackRoutePlan(should_escalate=False, trigger_reasons=())

    conflict = _has_conflicting_hypotheses(result)
    if bool(rules.get("conflicting_hypotheses_required", False)) and not conflict:
        return CloudFallbackRoutePlan(should_escalate=False, trigger_reasons=())

    confidence = float(result["summary"]["confidence"])
    confidence_below = confidence <= float(rules["local_confidence_below"])

    if not (confidence_below or conflict):
        return CloudFallbackRoutePlan(should_escalate=False, trigger_reasons=())

    reasons: list[str] = []
    if confidence_below:
        reasons.append("local_confidence_below_cloud_gate")
    if has_unknowns and bool(rules.get("unresolved_unknowns_required", False)):
        reasons.append("unresolved_unknowns_cloud_gate")
    if conflict:
        reasons.append("conflicting_hypotheses_cloud_gate")

    return CloudFallbackRoutePlan(
        should_escalate=True,
        trigger_reasons=tuple(reasons),
    )



def plan_investigation(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    config: InvestigatorRoutingConfig,
) -> InvestigationRoutePlan:
    if decision["packet_id"] != packet["packet_id"]:
        raise ValueError("decision packet_id must match incident packet")

    default_trigger_reasons = tuple(decision["investigation_trigger_reasons"])
    if config.routing.require_needs_investigation and not decision["needs_investigation"]:
        return InvestigationRoutePlan(
            mode=config.default_mode,
            should_investigate=False,
            selected_provider=None,
            provider_order=config.routing.allowed_provider_order,
            trigger_reasons=default_trigger_reasons,
            allow_cloud_fallback=config.routing.allow_cloud_fallback,
            budget=None,
            request=None,
        )

    if not config.local_primary.enabled:
        raise ValueError("local_primary investigator must remain enabled in local_first mode")

    route_reasons = _local_primary_route_reasons(packet, decision, config=config)
    if not route_reasons:
        return InvestigationRoutePlan(
            mode=config.default_mode,
            should_investigate=False,
            selected_provider=None,
            provider_order=config.routing.allowed_provider_order,
            trigger_reasons=default_trigger_reasons,
            allow_cloud_fallback=config.routing.allow_cloud_fallback,
            budget=None,
            request=None,
        )

    request = build_investigation_request(packet, decision, budget=config.local_primary.budget)
    return InvestigationRoutePlan(
        mode=config.default_mode,
        should_investigate=True,
        selected_provider="local_primary",
        provider_order=config.routing.allowed_provider_order,
        trigger_reasons=route_reasons,
        allow_cloud_fallback=config.routing.allow_cloud_fallback,
        budget=config.local_primary.budget,
        request=request,
    )
