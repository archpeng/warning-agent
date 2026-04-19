"""Investigator interface contract for the local-first routing layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.contracts import InvestigationResult
from app.packet.contracts import IncidentPacket

InvestigatorMode = Literal["local_first"]
ProviderName = Literal["local_primary", "cloud_fallback"]


@dataclass(frozen=True)
class InvestigatorBudget:
    wall_time_seconds: int
    max_tool_calls: int
    max_prompt_tokens: int
    max_completion_tokens: int
    max_retrieval_refs: int
    max_trace_refs: int
    max_log_refs: int
    max_code_refs: int


@dataclass(frozen=True)
class InvestigationRequest:
    packet: IncidentPacket
    decision: LocalAnalyzerDecision
    budget: InvestigatorBudget
    retrieval_packet_ids: tuple[str, ...]
    prometheus_query_refs: tuple[str, ...]
    signoz_query_refs: tuple[str, ...]
    sample_trace_ids: tuple[str, ...]
    sample_log_refs: tuple[str, ...]
    code_search_refs: tuple[str, ...] = ()


class InvestigatorProvider(Protocol):
    provider_name: ProviderName

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        ...


def build_investigation_request(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    budget: InvestigatorBudget,
    code_search_refs: tuple[str, ...] = (),
) -> InvestigationRequest:
    retrieval_packet_ids = tuple(hit["packet_id"] for hit in decision["retrieval_hits"][: budget.max_retrieval_refs])
    prometheus_query_refs = tuple(packet["evidence_refs"]["prometheus_query_refs"][: budget.max_tool_calls])
    signoz_query_refs = tuple(packet["evidence_refs"]["signoz_query_refs"][: budget.max_tool_calls])
    sample_trace_ids = tuple(packet["signoz"]["sample_trace_ids"][: budget.max_trace_refs])
    sample_log_refs = tuple(packet["signoz"]["sample_log_refs"][: budget.max_log_refs])

    return InvestigationRequest(
        packet=packet,
        decision=decision,
        budget=budget,
        retrieval_packet_ids=retrieval_packet_ids,
        prometheus_query_refs=prometheus_query_refs,
        signoz_query_refs=signoz_query_refs,
        sample_trace_ids=sample_trace_ids,
        sample_log_refs=sample_log_refs,
        code_search_refs=code_search_refs[: budget.max_code_refs],
    )
