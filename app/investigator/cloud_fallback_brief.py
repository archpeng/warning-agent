"""Bounded handoff/brief objects and request mapping for cloud-fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.contracts import InvestigationResult
from app.investigator.local_primary import build_investigation_id
from app.investigator.router import CloudFallbackAuditConfig, CloudFallbackBudget, load_investigator_routing_config
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



def _estimate_tokens(markdown: str) -> int:
    return max(1, (len(markdown) + 3) // 4)



def _inline(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"



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
