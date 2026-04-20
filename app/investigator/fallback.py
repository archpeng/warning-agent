"""Degraded local fallback for local-primary investigation failures."""

from __future__ import annotations

from typing import Protocol

from app.analyzer.contracts import LocalAnalyzerDecision
from app.investigator.base import InvestigationRequest
from app.investigator.contracts import InvestigationResult
from app.investigator.local_primary import (
    LocalPrimaryAbnormalPathDecision,
    LocalPrimaryResidentLifecycle,
    build_investigation_id,
)
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
    resident_lifecycle: LocalPrimaryResidentLifecycle | None = None,
    abnormal_path: LocalPrimaryAbnormalPathDecision | None = None,
) -> InvestigationResult:
    boundary = load_provider_boundary_config().local_primary
    reason_codes = list(decision["reason_codes"][:4])
    if "degraded_local_fallback" not in reason_codes:
        reason_codes.append("degraded_local_fallback")
    if resident_lifecycle is not None:
        lifecycle_reason_code = f"local_primary_resident_{resident_lifecycle.state}"
        if lifecycle_reason_code not in reason_codes and len(reason_codes) < 10:
            reason_codes.append(lifecycle_reason_code)
    fallback_recommended_action = boundary.fail_closed_recommended_action

    notes = [
        "degraded_local_fallback",
        f"local_primary_provider_mode={boundary.mode}",
        f"local_primary_current_smoke_model={boundary.smoke.model_name}",
        f"local_primary_future_real_adapter={boundary.real_adapter.adapter}",
        (
            "local_primary_future_real_adapter_enabled_env="
            f"{boundary.real_adapter.enabled_env}"
        ),
        f"fail_closed_to={fallback_recommended_action}",
        failure_reason,
    ]
    if resident_lifecycle is not None:
        notes.extend(
            [
                f"local_primary_resident_state={resident_lifecycle.state}",
                f"local_primary_resident_gate_state={resident_lifecycle.gate_state}",
                f"local_primary_resident_provider_mode={resident_lifecycle.provider_mode}",
            ]
        )
    if abnormal_path is not None:
        notes.append(f"local_primary_abnormal_action={abnormal_path.action}")
        notes.append(f"local_primary_abnormal_runtime_context={abnormal_path.runtime_context}")
        if abnormal_path.fallback_provider is not None:
            notes.append(f"local_primary_abnormal_fallback_provider={abnormal_path.fallback_provider}")
        if abnormal_path.queue_policy is not None:
            notes.append(f"local_primary_abnormal_queue_policy={abnormal_path.queue_policy}")

    unknowns = [
        failure_reason,
        "deep local follow-up did not complete; bounded tool wrappers may need another pass",
    ]
    if abnormal_path is not None and abnormal_path.reason not in unknowns:
        unknowns.append(abnormal_path.reason)

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
            "notes": notes,
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
        "unknowns": unknowns,
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
