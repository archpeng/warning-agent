"""Minimal internal records for investigator-side future learning groundwork."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.investigator.cloud_fallback_brief import CloudFallbackRequest
from app.investigator.contracts import InvestigationResult

ActionStepKind = Literal["route", "local_primary", "cloud_fallback", "recovery_wait"]
ActionOutcome = Literal["selected", "completed", "escalated", "deferred"]


@dataclass(frozen=True)
class ActionTraceStep:
    step_kind: ActionStepKind
    action: str
    outcome: ActionOutcome
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionTrace:
    packet_id: str
    decision_id: str
    steps: tuple[ActionTraceStep, ...]
    stop_reason: str


@dataclass(frozen=True)
class InvestigationEvidencePack:
    packet_id: str
    decision_id: str
    retrieval_packet_ids: tuple[str, ...]
    prometheus_ref_ids: tuple[str, ...]
    signoz_ref_ids: tuple[str, ...]
    trace_ids: tuple[str, ...]
    code_refs: tuple[str, ...]
    strongest_signal_notes: tuple[str, ...]
    conflicting_signal_notes: tuple[str, ...]


@dataclass(frozen=True)
class CompressedInvestigationBrief:
    packet_id: str
    decision_id: str
    parent_investigation_id: str
    handoff_markdown: str
    handoff_tokens_estimate: int
    carry_reason_codes: tuple[str, ...]
    omitted_context: tuple[str, ...]



def build_action_trace(
    *,
    packet_id: str,
    decision_id: str,
    route_selected_provider: str | None,
    cloud_trigger_reasons: tuple[str, ...] = (),
    recovery_wait_reason: str | None = None,
    final_result: InvestigationResult | None = None,
) -> ActionTrace:
    steps: list[ActionTraceStep] = []
    if route_selected_provider is not None:
        steps.append(
            ActionTraceStep(
                step_kind="route",
                action=f"select_{route_selected_provider}",
                outcome="selected",
            )
        )
    if final_result is not None and final_result["investigator_tier"] == "local_primary_investigator":
        steps.append(
            ActionTraceStep(
                step_kind="local_primary",
                action="run_local_primary",
                outcome="completed",
                notes=tuple(str(note) for note in final_result["analysis_updates"]["notes"][:3]),
            )
        )
    if cloud_trigger_reasons:
        steps.append(
            ActionTraceStep(
                step_kind="cloud_fallback",
                action="escalate_to_cloud_fallback",
                outcome="escalated",
                notes=cloud_trigger_reasons,
            )
        )
    if final_result is not None and final_result["investigator_tier"] == "cloud_fallback_investigator":
        steps.append(
            ActionTraceStep(
                step_kind="cloud_fallback",
                action="run_cloud_fallback",
                outcome="completed",
                notes=tuple(str(note) for note in final_result["analysis_updates"]["notes"][:3]),
            )
        )
    if recovery_wait_reason is not None:
        steps.append(
            ActionTraceStep(
                step_kind="recovery_wait",
                action="wait_for_local_primary_recovery",
                outcome="deferred",
                notes=(recovery_wait_reason,),
            )
        )

    stop_reason = recovery_wait_reason or (
        "final_result_available" if final_result is not None else "route_selected_without_final_result"
    )
    return ActionTrace(
        packet_id=packet_id,
        decision_id=decision_id,
        steps=tuple(steps),
        stop_reason=stop_reason,
    )



def build_investigation_evidence_pack(result: InvestigationResult) -> InvestigationEvidencePack:
    summary = result["summary"]
    return InvestigationEvidencePack(
        packet_id=result["packet_id"],
        decision_id=result["decision_id"],
        retrieval_packet_ids=tuple(result["input_refs"].get("retrieval_packet_ids", [])),
        prometheus_ref_ids=tuple(result["evidence_refs"]["prometheus_ref_ids"]),
        signoz_ref_ids=tuple(result["evidence_refs"]["signoz_ref_ids"]),
        trace_ids=tuple(result["evidence_refs"]["trace_ids"]),
        code_refs=tuple(result["evidence_refs"]["code_refs"]),
        strongest_signal_notes=tuple(str(code) for code in summary["reason_codes"][:4]),
        conflicting_signal_notes=tuple(str(item) for item in result["unknowns"][:2]),
    )



def build_compressed_investigation_brief(request: CloudFallbackRequest) -> CompressedInvestigationBrief:
    parent = request.parent_investigation
    input_refs = parent["input_refs"]
    evidence_refs = parent["evidence_refs"]
    omitted_context: list[str] = []
    if len(input_refs.get("retrieval_packet_ids", [])) > 3:
        omitted_context.append("retrieval_packet_ids_truncated_to_top3")
    if len(evidence_refs["prometheus_ref_ids"]) > 3:
        omitted_context.append("prometheus_refs_truncated_to_top3")
    if len(evidence_refs["signoz_ref_ids"]) > 3:
        omitted_context.append("signoz_refs_truncated_to_top3")
    if len(evidence_refs["code_refs"]) > 3:
        omitted_context.append("code_refs_truncated_to_top3")

    return CompressedInvestigationBrief(
        packet_id=request.packet["packet_id"],
        decision_id=request.decision["decision_id"],
        parent_investigation_id=parent["investigation_id"],
        handoff_markdown=request.handoff_markdown,
        handoff_tokens_estimate=request.handoff_tokens_estimate,
        carry_reason_codes=request.carry_reason_codes,
        omitted_context=tuple(omitted_context),
    )



def action_trace_payload(trace: ActionTrace) -> dict[str, object]:
    return {
        "packet_id": trace.packet_id,
        "decision_id": trace.decision_id,
        "steps": [
            {
                "step_kind": step.step_kind,
                "action": step.action,
                "outcome": step.outcome,
                "notes": list(step.notes),
            }
            for step in trace.steps
        ],
        "stop_reason": trace.stop_reason,
    }



def investigation_evidence_pack_payload(pack: InvestigationEvidencePack) -> dict[str, object]:
    return {
        "packet_id": pack.packet_id,
        "decision_id": pack.decision_id,
        "retrieval_packet_ids": list(pack.retrieval_packet_ids),
        "prometheus_ref_ids": list(pack.prometheus_ref_ids),
        "signoz_ref_ids": list(pack.signoz_ref_ids),
        "trace_ids": list(pack.trace_ids),
        "code_refs": list(pack.code_refs),
        "strongest_signal_notes": list(pack.strongest_signal_notes),
        "conflicting_signal_notes": list(pack.conflicting_signal_notes),
    }



def compressed_investigation_brief_payload(brief: CompressedInvestigationBrief) -> dict[str, object]:
    return {
        "packet_id": brief.packet_id,
        "decision_id": brief.decision_id,
        "parent_investigation_id": brief.parent_investigation_id,
        "handoff_markdown": brief.handoff_markdown,
        "handoff_tokens_estimate": brief.handoff_tokens_estimate,
        "carry_reason_codes": list(brief.carry_reason_codes),
        "omitted_context": list(brief.omitted_context),
    }
