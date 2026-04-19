"""Degraded local fallback for local-primary investigation failures."""

from __future__ import annotations

from typing import Protocol

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.base import InvestigationRequest
from app.investigator.contracts import InvestigationResult
from app.investigator.local_primary import build_investigation_id
from app.investigator.provider_boundary import load_provider_boundary_config
from app.packet.contracts import IncidentPacket


class LocalPrimaryProviderProtocol(Protocol):
    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        ...


def build_degraded_local_fallback(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    *,
    failure_reason: str,
) -> InvestigationResult:
    boundary = load_provider_boundary_config().local_primary
    reason_codes = list(decision["reason_codes"][:4])
    if "degraded_local_fallback" not in reason_codes:
        reason_codes.append("degraded_local_fallback")
    fallback_recommended_action = boundary.fail_closed_recommended_action

    return {
        "schema_version": "investigation-result.v1",
        "investigation_id": build_investigation_id(packet) + "_degraded",
        "packet_id": packet["packet_id"],
        "decision_id": decision["decision_id"],
        "investigator_tier": "local_primary_investigator",
        "model_provider": "local_vllm",
        "model_name": "local-primary-degraded-fallback",
        "generated_at": packet["created_at"],
        "input_refs": {
            "packet_id": packet["packet_id"],
            "decision_id": decision["decision_id"],
            "retrieval_packet_ids": [hit["packet_id"] for hit in decision["retrieval_hits"]],
            "prometheus_query_refs": packet["evidence_refs"]["prometheus_query_refs"],
            "signoz_query_refs": packet["evidence_refs"]["signoz_query_refs"],
            "code_search_refs": [],
            "upstream_report_id": None,
        },
        "summary": {
            "investigation_used": True,
            "severity_band": decision["severity_band"],
            "recommended_action": fallback_recommended_action,
            "confidence": decision["confidence"],
            "reason_codes": reason_codes,
            "suspected_primary_cause": "local-primary investigation degraded before bounded follow-up completed",
            "failure_chain_summary": (
                f"{packet['service']} {packet['operation']} stayed on the degraded local path because "
                f"{failure_reason}."
            ),
        },
        "hypotheses": [
            {
                "rank": 1,
                "hypothesis": "bounded local follow-up did not complete; preserve first-pass routing until deeper investigation is available",
                "confidence": decision["confidence"],
                "supporting_reason_codes": reason_codes,
            }
        ],
        "analysis_updates": {
            "severity_band_changed": False,
            "recommended_action_changed": decision["recommended_action"] != fallback_recommended_action,
            "fallback_invocation_was_correct": True,
            "notes": [
                "degraded_local_fallback",
                f"provider_mode={boundary.mode}",
                f"fail_closed_to={fallback_recommended_action}",
                failure_reason,
            ],
        },
        "routing": {
            "owner_hint": packet["topology"]["owner"],
            "repo_candidates": packet["topology"]["repo_candidates"],
            "suspected_code_paths": [],
            "escalation_target": packet["topology"]["owner"],
        },
        "evidence_refs": {
            "prometheus_ref_ids": packet["evidence_refs"]["prometheus_query_refs"],
            "signoz_ref_ids": packet["evidence_refs"]["signoz_query_refs"],
            "trace_ids": packet["signoz"]["sample_trace_ids"],
            "code_refs": [],
        },
        "unknowns": [
            failure_reason,
            "deep local follow-up did not complete; bounded tool wrappers may need another pass",
        ],
    }


def run_local_primary_with_fallback(
    packet: IncidentPacket,
    decision: LocalAnalyzerDecision,
    request: InvestigationRequest,
    *,
    provider: LocalPrimaryProviderProtocol,
) -> InvestigationResult:
    try:
        return provider.investigate(request)
    except Exception as exc:  # pragma: no cover - exercised by tests through failure injection
        return build_degraded_local_fallback(packet, decision, failure_reason=str(exc))
