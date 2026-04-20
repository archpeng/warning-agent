"""Deterministic cloud-fallback investigator smoke provider."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Mapping, Protocol

from app.analyzer.base import round_score
from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.contracts import InvestigationResult
from app.investigator.local_primary import build_investigation_id
from app.investigator.provider_boundary import load_provider_boundary_config, resolve_real_adapter_gate
from app.investigator.router import (
    CloudFallbackAuditConfig,
    CloudFallbackBudget,
    load_investigator_routing_config,
)
from app.packet.contracts import IncidentPacket


@dataclass(frozen=True)
class CloudFallbackRequest:
    packet: IncidentPacket
    decision: LocalAnalyzerDecision
    parent_investigation: InvestigationResult
    budget: CloudFallbackBudget
    audit: CloudFallbackAuditConfig
    handoff_markdown: str
    handoff_tokens_estimate: int
    carry_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CloudFallbackClientRequest:
    investigation_id: str
    parent_investigation_id: str
    packet_id: str
    decision_id: str
    handoff_markdown: str
    handoff_tokens_estimate: int
    carry_reason_codes: tuple[str, ...]
    retrieval_packet_ids: tuple[str, ...]
    prometheus_query_refs: tuple[str, ...]
    signoz_query_refs: tuple[str, ...]
    trace_ids: tuple[str, ...]
    repo_candidates: tuple[str, ...]
    code_refs: tuple[str, ...]


@dataclass(frozen=True)
class CloudFallbackHypothesis:
    hypothesis: str
    confidence: float
    supporting_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CloudFallbackClientResponse:
    severity_band: str
    recommended_action: str
    confidence: float
    suspected_primary_cause: str
    failure_chain_summary: str
    hypotheses: tuple[CloudFallbackHypothesis, ...]
    unknowns: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class CloudFallbackAuditRecord:
    packet_id: str
    parent_investigation_id: str
    result_investigation_id: str
    result_investigator_tier: str
    handoff_tokens_estimate: int
    wall_time_seconds: float
    fallback_used: bool
    failure_reason: str | None


@dataclass(frozen=True)
class CloudFallbackGuardSnapshot:
    total_packets: int
    investigated_packets: int
    cloud_fallback_invocation_count: int
    wall_time_seconds: tuple[float, ...]
    handoff_tokens_estimates: tuple[int, ...]


class CloudFallbackClient(Protocol):
    def investigate(self, request: CloudFallbackClientRequest) -> CloudFallbackClientResponse:
        ...


class CloudFallbackProvider(Protocol):
    def investigate(self, request: CloudFallbackRequest) -> InvestigationResult:
        ...



def build_real_cloud_fallback_client(
    *,
    boundary,
    gate,
):
    if gate.state != "ready":
        raise ValueError("real cloud_fallback client can only be built when gate state is ready")
    if gate.transport != "openai_responses_api":
        raise RuntimeError(f"unsupported cloud_fallback real adapter transport: {gate.transport}")
    if gate.endpoint is None or gate.model_name is None or gate.api_key is None:
        raise RuntimeError("cloud_fallback real adapter gate ready but endpoint/model/api_key missing")

    from app.investigator.cloud_fallback_openai_responses import CloudFallbackOpenAIResponsesClient

    return CloudFallbackOpenAIResponsesClient(
        endpoint=gate.endpoint,
        api_key=gate.api_key,
        model_name=gate.model_name,
        timeout_seconds=boundary.real_adapter.timeout_seconds,
        model_provider=boundary.operating_contract.target_model_provider,
    )


@dataclass(frozen=True)
class DeterministicCloudFallbackClient:
    def investigate(self, request: CloudFallbackClientRequest) -> CloudFallbackClientResponse:
        handoff_fields = parse_cloud_handoff_markdown(request.handoff_markdown)
        service = handoff_fields.get("service", "unknown-service")
        operation = handoff_fields.get("operation", service)
        cause = handoff_fields.get(
            "suspected_primary_cause",
            "local-primary handoff remained unresolved before bounded cloud review",
        )
        severity_band = handoff_fields.get("severity_band", "P3")
        recommended_action = handoff_fields.get("recommended_action", "send_to_human_review")
        parent_confidence = _parse_float(handoff_fields.get("parent_confidence"), default=0.55)
        supporting_codes = request.carry_reason_codes[:4] or ("cloud_fallback_smoke",)
        confidence = round_score(min(0.92, parent_confidence + 0.08))
        review_target = request.code_refs[0] if request.code_refs else request.repo_candidates[0]
        local_unknowns = _split_inline(handoff_fields.get("local_unknowns", ""))
        local_unknown = (
            local_unknowns[0]
            if local_unknowns
            else "local-primary handoff remained unresolved before bounded cloud review"
        )

        hypotheses = (
            CloudFallbackHypothesis(
                hypothesis=(
                    f"cloud fallback confirms {cause} as the most likely driver of the "
                    f"{service} regression on {operation}"
                ),
                confidence=confidence,
                supporting_reason_codes=supporting_codes,
            ),
            CloudFallbackHypothesis(
                hypothesis=f"next validation should inspect {review_target} before broader mitigation decisions",
                confidence=round_score(max(0.45, confidence - 0.17)),
                supporting_reason_codes=("cloud_handoff_review",),
            ),
        )

        return CloudFallbackClientResponse(
            severity_band=severity_band,
            recommended_action=recommended_action,
            confidence=confidence,
            suspected_primary_cause=cause,
            failure_chain_summary=(
                f"cloud fallback reviewed the bounded local handoff for {service} {operation} "
                f"and retained {cause} as the leading failure chain driver."
            ),
            hypotheses=hypotheses,
            unknowns=(
                local_unknown,
                "deterministic cloud fallback smoke client is active; live vendor API integration remains pending",
            ),
            notes=(
                "cloud_fallback_smoke_result",
                f"handoff_tokens_estimate={request.handoff_tokens_estimate}",
            ),
        )


def _generated_at(packet: IncidentPacket, *, offset_seconds: int = 16) -> str:
    created_at = str(packet["created_at"])
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC) + timedelta(
        seconds=offset_seconds
    )
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _estimate_tokens(markdown: str) -> int:
    return max(1, (len(markdown) + 3) // 4)


def _inline(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _split_inline(value: str) -> tuple[str, ...]:
    if not value or value == "none":
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_float(value: str | None, *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _p95(values: tuple[float, ...] | tuple[int, ...]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, (len(ordered) * 95 + 99) // 100 - 1)
    return ordered[index]


def parse_cloud_handoff_markdown(markdown: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in markdown.splitlines():
        if not line.startswith("- ") or ": " not in line:
            continue
        key, value = line[2:].split(": ", maxsplit=1)
        fields[key.strip()] = value.strip()
    return fields


def build_cloud_handoff_markdown(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    parent_investigation: InvestigationResult,
) -> str:
    parent_summary = parent_investigation["summary"]
    parent_routing = parent_investigation["routing"]
    parent_input_refs = parent_investigation["input_refs"]
    parent_evidence_refs = parent_investigation["evidence_refs"]
    top_hypothesis = parent_investigation["hypotheses"][0]["hypothesis"]

    lines = [
        "# Cloud Fallback Handoff",
        f"- packet_id: {packet['packet_id']}",
        f"- decision_id: {decision['decision_id']}",
        f"- parent_investigation_id: {parent_investigation['investigation_id']}",
        f"- service: {packet['service']}",
        f"- operation: {packet['operation']}",
        f"- severity_band: {parent_summary['severity_band']}",
        f"- recommended_action: {parent_summary['recommended_action']}",
        f"- parent_confidence: {parent_summary['confidence']}",
        f"- suspected_primary_cause: {parent_summary['suspected_primary_cause']}",
        f"- top_hypothesis: {top_hypothesis}",
        f"- owner_hint: {parent_routing['owner_hint'] or 'none'}",
        f"- repo_candidates: {_inline(tuple(parent_routing['repo_candidates'][:2]))}",
        f"- retrieval_packet_ids: {_inline(tuple(parent_input_refs.get('retrieval_packet_ids', [])[:3]))}",
        f"- prometheus_refs: {_inline(tuple(parent_evidence_refs['prometheus_ref_ids'][:3]))}",
        f"- signoz_refs: {_inline(tuple(parent_evidence_refs['signoz_ref_ids'][:3]))}",
        f"- code_refs: {_inline(tuple(parent_evidence_refs['code_refs'][:3]))}",
        f"- local_unknowns: {_inline(tuple(parent_investigation['unknowns'][:2]))}",
    ]
    return "\n".join(lines)


def build_cloud_fallback_request(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    parent_investigation: InvestigationResult,
    *,
    config_path: str | Path = Path("configs/escalation.yaml"),
) -> CloudFallbackRequest:
    if decision["packet_id"] != packet["packet_id"]:
        raise ValueError("decision packet_id must match incident packet for cloud fallback")
    if parent_investigation["packet_id"] != packet["packet_id"]:
        raise ValueError("parent investigation packet_id must match incident packet")
    if parent_investigation["decision_id"] != decision["decision_id"]:
        raise ValueError("parent investigation decision_id must match local analyzer decision")
    if parent_investigation["investigator_tier"] != "local_primary_investigator":
        raise ValueError("cloud fallback currently requires a local-primary parent investigation")

    config = load_investigator_routing_config(config_path)
    handoff_markdown = build_cloud_handoff_markdown(packet, decision, parent_investigation)
    handoff_tokens_estimate = _estimate_tokens(handoff_markdown)
    if handoff_tokens_estimate > config.cloud_fallback.budget.max_handoff_tokens:
        raise ValueError("compressed handoff exceeded cloud fallback token budget")

    carry_reason_codes = tuple(parent_investigation["summary"]["reason_codes"][:4])
    if not carry_reason_codes:
        carry_reason_codes = tuple(decision["reason_codes"][:4])
    if not carry_reason_codes:
        carry_reason_codes = ("cloud_fallback_smoke",)

    return CloudFallbackRequest(
        packet=packet,
        decision=decision,
        parent_investigation=parent_investigation,
        budget=config.cloud_fallback.budget,
        audit=config.cloud_fallback.audit,
        handoff_markdown=handoff_markdown,
        handoff_tokens_estimate=handoff_tokens_estimate,
        carry_reason_codes=carry_reason_codes,
    )


def build_cloud_client_request(request: CloudFallbackRequest) -> CloudFallbackClientRequest:
    parent_routing = request.parent_investigation["routing"]
    evidence_refs = request.parent_investigation["evidence_refs"]
    parent_input_refs = request.parent_investigation["input_refs"]

    return CloudFallbackClientRequest(
        investigation_id=build_investigation_id(request.packet, offset_seconds=16) + "_cloud",
        parent_investigation_id=request.parent_investigation["investigation_id"],
        packet_id=request.packet["packet_id"],
        decision_id=request.decision["decision_id"],
        handoff_markdown=request.handoff_markdown,
        handoff_tokens_estimate=request.handoff_tokens_estimate,
        carry_reason_codes=request.carry_reason_codes[:4],
        retrieval_packet_ids=tuple(parent_input_refs.get("retrieval_packet_ids", [])[:3]),
        prometheus_query_refs=tuple(evidence_refs["prometheus_ref_ids"][:3]),
        signoz_query_refs=tuple(evidence_refs["signoz_ref_ids"][:3]),
        trace_ids=tuple(evidence_refs["trace_ids"][:3]),
        repo_candidates=tuple(parent_routing["repo_candidates"][:3]),
        code_refs=tuple(evidence_refs["code_refs"][:3]),
    )


def build_cloud_unavailable_local_fallback(
    request: CloudFallbackRequest,
    *,
    failure_reason: str,
) -> InvestigationResult:
    boundary = load_provider_boundary_config().cloud_fallback
    fallback_result = deepcopy(request.parent_investigation)
    previous_recommended_action = fallback_result["summary"]["recommended_action"]
    reason_codes = list(fallback_result["summary"]["reason_codes"])
    if "cloud_fallback_unavailable" not in reason_codes and len(reason_codes) < 10:
        reason_codes.append("cloud_fallback_unavailable")
    fallback_result["summary"]["reason_codes"] = reason_codes
    fallback_result["summary"]["recommended_action"] = boundary.fail_closed_recommended_action

    notes = list(fallback_result["analysis_updates"]["notes"])
    if "cloud_fallback_unavailable" not in notes:
        notes.append("cloud_fallback_unavailable")
    for note in (
        f"cloud_fallback_provider_mode={boundary.mode}",
        f"cloud_fallback_current_smoke_model={boundary.smoke.model_name}",
        f"cloud_fallback_future_real_adapter={boundary.real_adapter.adapter}",
        (
            "cloud_fallback_future_real_adapter_enabled_env="
            f"{boundary.real_adapter.enabled_env}"
        ),
        f"fail_closed_to={boundary.fail_closed_recommended_action}",
        f"cloud_fallback_failure_reason={failure_reason}",
    ):
        if note not in notes:
            notes.append(note)
    fallback_result["analysis_updates"]["notes"] = notes
    fallback_result["analysis_updates"]["recommended_action_changed"] = (
        previous_recommended_action != boundary.fail_closed_recommended_action
    )

    unknowns = list(fallback_result["unknowns"])
    unavailable_note = f"cloud fallback unavailable: {failure_reason}"
    if unavailable_note not in unknowns:
        unknowns.append(unavailable_note)
    fallback_result["unknowns"] = unknowns
    fallback_result["compressed_handoff"] = {
        "handoff_markdown": request.handoff_markdown,
        "handoff_tokens_estimate": request.handoff_tokens_estimate,
        "carry_reason_codes": list(request.carry_reason_codes[:4]),
    }
    return fallback_result


def build_cloud_audit_record(
    request: CloudFallbackRequest,
    result: InvestigationResult,
    *,
    wall_time_seconds: float,
    fallback_used: bool,
    failure_reason: str | None,
) -> CloudFallbackAuditRecord:
    return CloudFallbackAuditRecord(
        packet_id=request.packet["packet_id"],
        parent_investigation_id=request.parent_investigation["investigation_id"],
        result_investigation_id=result["investigation_id"],
        result_investigator_tier=result["investigator_tier"],
        handoff_tokens_estimate=request.handoff_tokens_estimate,
        wall_time_seconds=round(float(wall_time_seconds), 2),
        fallback_used=fallback_used,
        failure_reason=failure_reason,
    )


def evaluate_cloud_fallback_guards(
    snapshot: CloudFallbackGuardSnapshot,
    *,
    budget: CloudFallbackBudget,
) -> dict[str, object]:
    total_rate = (
        snapshot.cloud_fallback_invocation_count / snapshot.total_packets if snapshot.total_packets else 0.0
    )
    investigated_rate = (
        snapshot.cloud_fallback_invocation_count / snapshot.investigated_packets
        if snapshot.investigated_packets
        else 0.0
    )
    wall_time_p95 = _p95(snapshot.wall_time_seconds)
    handoff_tokens_p95 = _p95(snapshot.handoff_tokens_estimates)

    checks = {
        "cloud_fallback_rate_total": {
            "actual": round(total_rate, 4),
            "expected": budget.max_invocation_rate_total,
            "comparator": "<=",
            "passed": total_rate <= budget.max_invocation_rate_total,
        },
        "cloud_fallback_rate_investigated": {
            "actual": round(investigated_rate, 4),
            "expected": budget.max_invocation_rate_investigated,
            "comparator": "<=",
            "passed": investigated_rate <= budget.max_invocation_rate_investigated,
        },
        "cloud_fallback_p95_wall_time_sec": {
            "actual": round(wall_time_p95, 4),
            "expected": budget.max_wall_time_seconds,
            "comparator": "<=",
            "passed": wall_time_p95 <= budget.max_wall_time_seconds,
        },
        "compressed_handoff_p95_tokens": {
            "actual": round(handoff_tokens_p95, 4),
            "expected": budget.max_handoff_tokens,
            "comparator": "<=",
            "passed": handoff_tokens_p95 <= budget.max_handoff_tokens,
        },
    }

    blockers: list[str] = []
    if not checks["cloud_fallback_rate_total"]["passed"]:
        blockers.append("cloud_fallback_rate_total_above_gate")
    if not checks["cloud_fallback_rate_investigated"]["passed"]:
        blockers.append("cloud_fallback_rate_investigated_above_gate")
    if not checks["cloud_fallback_p95_wall_time_sec"]["passed"]:
        blockers.append("cloud_fallback_wall_time_above_gate")
    if not checks["compressed_handoff_p95_tokens"]["passed"]:
        blockers.append("compressed_handoff_tokens_above_gate")

    return {
        "accepted": not blockers,
        "blockers": blockers,
        "metrics": {
            "total_packets": snapshot.total_packets,
            "investigated_packets": snapshot.investigated_packets,
            "cloud_fallback_invocation_count": snapshot.cloud_fallback_invocation_count,
            "cloud_fallback_rate_total": round(total_rate, 4),
            "cloud_fallback_rate_investigated": round(investigated_rate, 4),
            "cloud_fallback_p95_wall_time_sec": round(wall_time_p95, 4),
            "compressed_handoff_p95_tokens": round(handoff_tokens_p95, 4),
        },
        "checks": checks,
    }


def run_cloud_fallback_with_local_fallback(
    request: CloudFallbackRequest,
    *,
    provider: CloudFallbackProvider,
    wall_time_seconds: float = 0.0,
) -> tuple[InvestigationResult, CloudFallbackAuditRecord]:
    try:
        result = provider.investigate(request)
        audit = build_cloud_audit_record(
            request,
            result,
            wall_time_seconds=wall_time_seconds,
            fallback_used=False,
            failure_reason=None,
        )
        return result, audit
    except Exception as exc:  # pragma: no cover - exercised by tests via failure injection
        fallback_result = build_cloud_unavailable_local_fallback(request, failure_reason=str(exc))
        audit = build_cloud_audit_record(
            request,
            fallback_result,
            wall_time_seconds=wall_time_seconds,
            fallback_used=True,
            failure_reason=str(exc),
        )
        return fallback_result, audit


@dataclass(frozen=True)
class CloudFallbackInvestigator:
    budget: CloudFallbackBudget
    audit: CloudFallbackAuditConfig
    model_provider: str
    model_name: str
    client: CloudFallbackClient
    env: Mapping[str, str | None] = field(default_factory=lambda: os.environ)
    real_adapter_client: CloudFallbackClient | None = None
    provider_name: str = "cloud_fallback"

    @classmethod
    def from_config(
        cls,
        config_path: str | Path = Path("configs/escalation.yaml"),
        *,
        client: CloudFallbackClient | None = None,
        env: Mapping[str, str | None] = os.environ,
        real_adapter_client: CloudFallbackClient | None = None,
    ) -> "CloudFallbackInvestigator":
        config = load_investigator_routing_config(config_path)
        boundary = load_provider_boundary_config().cloud_fallback
        gate = resolve_real_adapter_gate(boundary, env=env)
        if real_adapter_client is None and gate.state == "ready":
            real_adapter_client = build_real_cloud_fallback_client(boundary=boundary, gate=gate)
        return cls(
            budget=config.cloud_fallback.budget,
            audit=config.cloud_fallback.audit,
            model_provider=config.cloud_fallback.model_provider,
            model_name=config.cloud_fallback.model_name,
            client=client or DeterministicCloudFallbackClient(),
            env=env,
            real_adapter_client=real_adapter_client,
        )

    def investigate(self, request: CloudFallbackRequest) -> InvestigationResult:
        if request.budget != self.budget:
            raise ValueError("request budget must match cloud-fallback provider budget")
        if request.audit != self.audit:
            raise ValueError("request audit contract must match cloud-fallback provider audit config")
        if self.audit.require_parent_investigation_id and not request.parent_investigation["investigation_id"]:
            raise ValueError("cloud fallback requires a parent investigation id")
        if self.audit.require_handoff_markdown and not request.handoff_markdown:
            raise ValueError("cloud fallback requires handoff markdown")
        if self.audit.require_handoff_tokens_estimate and request.handoff_tokens_estimate < 0:
            raise ValueError("cloud fallback requires a non-negative handoff token estimate")

        client_request = build_cloud_client_request(request)
        parent_routing = request.parent_investigation["routing"]
        parent_input_refs = request.parent_investigation["input_refs"]
        parent_evidence_refs = request.parent_investigation["evidence_refs"]
        boundary = load_provider_boundary_config().cloud_fallback
        gate = resolve_real_adapter_gate(boundary, env=self.env)

        result_model_provider = self.model_provider
        result_model_name = self.model_name
        if gate.state == "missing_env":
            raise RuntimeError(
                "cloud_fallback real adapter gate enabled but missing env: "
                + ", ".join(gate.missing_env)
            )
        if gate.state == "ready":
            if self.real_adapter_client is None:
                raise RuntimeError(
                    f"cloud_fallback real adapter gate ready but client unavailable for {gate.adapter}"
                )
            response = self.real_adapter_client.investigate(client_request)
            result_model_name = gate.model_name or boundary.operating_contract.target_model_name
        else:
            response = self.client.investigate(client_request)

        analysis_notes = [
            *response.notes,
            f"cloud_fallback_provider_mode={boundary.mode}",
            f"cloud_fallback_current_smoke_model={boundary.smoke.model_name}",
            f"cloud_fallback_future_real_adapter={boundary.real_adapter.adapter}",
            (
                "cloud_fallback_future_real_adapter_enabled_env="
                f"{boundary.real_adapter.enabled_env}"
            ),
            f"cloud_fallback_target_model_provider={boundary.operating_contract.target_model_provider}",
            f"cloud_fallback_target_model_name={boundary.operating_contract.target_model_name}",
        ]
        if self.audit.require_failure_reason_note:
            analysis_notes.append("cloud_fallback_invoked_after_local_primary_handoff")

        return {
            "schema_version": "investigation-result.v1",
            "investigation_id": client_request.investigation_id,
            "packet_id": request.packet["packet_id"],
            "decision_id": request.decision["decision_id"],
            "parent_investigation_id": client_request.parent_investigation_id,
            "investigator_tier": "cloud_fallback_investigator",
            "model_provider": result_model_provider,
            "model_name": result_model_name,
            "generated_at": _generated_at(request.packet),
            "input_refs": {
                "packet_id": request.packet["packet_id"],
                "decision_id": request.decision["decision_id"],
                "retrieval_packet_ids": list(parent_input_refs.get("retrieval_packet_ids", [])),
                "prometheus_query_refs": list(parent_evidence_refs["prometheus_ref_ids"]),
                "signoz_query_refs": list(parent_evidence_refs["signoz_ref_ids"]),
                "code_search_refs": list(parent_evidence_refs["code_refs"]),
                "upstream_report_id": None,
            },
            "summary": {
                "investigation_used": True,
                "severity_band": response.severity_band,
                "recommended_action": response.recommended_action,
                "confidence": response.confidence,
                "reason_codes": list(request.carry_reason_codes[:4]),
                "suspected_primary_cause": response.suspected_primary_cause,
                "failure_chain_summary": response.failure_chain_summary,
            },
            "hypotheses": [
                {
                    "rank": index,
                    "hypothesis": hypothesis.hypothesis,
                    "confidence": hypothesis.confidence,
                    "supporting_reason_codes": list(hypothesis.supporting_reason_codes),
                }
                for index, hypothesis in enumerate(response.hypotheses, start=1)
            ],
            "analysis_updates": {
                "severity_band_changed": response.severity_band != request.decision["severity_band"],
                "recommended_action_changed": response.recommended_action != request.decision["recommended_action"],
                "fallback_invocation_was_correct": True,
                "notes": analysis_notes,
            },
            "routing": {
                "owner_hint": parent_routing["owner_hint"],
                "repo_candidates": list(parent_routing["repo_candidates"]),
                "suspected_code_paths": list(parent_routing["suspected_code_paths"]),
                "escalation_target": parent_routing["escalation_target"],
            },
            "evidence_refs": {
                "prometheus_ref_ids": list(parent_evidence_refs["prometheus_ref_ids"]),
                "signoz_ref_ids": list(parent_evidence_refs["signoz_ref_ids"]),
                "trace_ids": list(parent_evidence_refs["trace_ids"]),
                "code_refs": list(parent_evidence_refs["code_refs"]),
            },
            "unknowns": list(response.unknowns),
            "compressed_handoff": {
                "handoff_markdown": request.handoff_markdown,
                "handoff_tokens_estimate": request.handoff_tokens_estimate,
                "carry_reason_codes": list(request.carry_reason_codes[:4]),
            },
        }
