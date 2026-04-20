"""Minimal internal records for analyzer-side assist and decision audit groundwork."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.analyzer.base import AnalyzerFeatures
from app.analyzer.contracts import LocalAnalyzerDecision

InvestigationValueHint = Literal["low", "medium", "high"]
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SidecarAssistPacket:
    packet_id: str
    service: str
    operation: str | None
    suggested_query_terms: tuple[str, ...]
    ambiguity_flags: tuple[str, ...]
    investigation_value_hint: InvestigationValueHint
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionAuditRecord:
    decision_id: str
    packet_id: str
    analyzer_family: str
    severity_band: str
    recommended_action: str
    needs_investigation: bool
    investigation_trigger_reasons: tuple[str, ...]
    top_contributing_signals: tuple[str, ...]
    ambiguity_flags: tuple[str, ...]
    confidence_context: tuple[str, ...]
    expected_value_hint: InvestigationValueHint



def _tokenize(value: str) -> list[str]:
    tokens = [token for token in _NON_ALNUM.sub(" ", value.lower()).split() if len(token) >= 3]
    deduped: list[str] = []
    for token in tokens:
        if token not in deduped:
            deduped.append(token)
    return deduped



def _ambiguity_flags(features: AnalyzerFeatures) -> tuple[str, ...]:
    flags: list[str] = []
    if features.retrieval_conflict >= 1.0:
        flags.append("retrieval_conflict")
    if features.owner_unknown >= 1.0:
        flags.append("owner_unknown")
    if features.novelty_signal >= 0.75:
        flags.append("novelty_high")
    return tuple(flags)



def _investigation_value_hint(
    decision: LocalAnalyzerDecision,
    *,
    features: AnalyzerFeatures,
) -> InvestigationValueHint:
    if not decision["needs_investigation"]:
        return "low"
    if decision["recommended_action"] == "page_owner":
        return "high"
    if decision["severity_band"] in {"P1", "P2"}:
        return "high"
    if features.retrieval_conflict >= 1.0 or features.novelty_signal >= 0.85:
        return "high"
    return "medium"



def _top_contributing_signals(features: AnalyzerFeatures) -> tuple[str, ...]:
    scored = [
        (features.error_rate_spike, "error_rate_spike"),
        (features.latency_spike, "latency_spike"),
        (features.trace_error_ratio, "trace_error_ratio"),
        (features.blast_radius_score, "blast_radius"),
        (features.novelty_signal, "novelty_signal"),
        (features.severe_retrieval_similarity, "severe_retrieval_similarity"),
        (features.signoz_alert_signal, "signoz_alert_signal"),
    ]
    ranked = [name for score, name in sorted(scored, reverse=True) if score > 0.0]
    return tuple(ranked[:4])



def build_sidecar_assist_packet(
    packet: dict[str, object],
    *,
    features: AnalyzerFeatures,
    decision: LocalAnalyzerDecision,
) -> SidecarAssistPacket:
    service = str(packet["service"])
    operation = packet.get("operation")
    signoz = packet.get("signoz") or {}
    top_error_templates = signoz.get("top_error_templates") or []
    template = ""
    if top_error_templates and isinstance(top_error_templates[0], dict):
        template = str(top_error_templates[0].get("template") or top_error_templates[0].get("body") or "")

    query_terms: list[str] = []
    for source in [service, str(operation or ""), template]:
        for token in _tokenize(source):
            if token not in query_terms:
                query_terms.append(token)

    return SidecarAssistPacket(
        packet_id=str(packet["packet_id"]),
        service=service,
        operation=str(operation) if operation is not None else None,
        suggested_query_terms=tuple(query_terms[:8]),
        ambiguity_flags=_ambiguity_flags(features),
        investigation_value_hint=_investigation_value_hint(decision, features=features),
        notes=("minimal_internal_assist_groundwork",),
    )



def build_decision_audit_record(
    *,
    packet: dict[str, object],
    decision: LocalAnalyzerDecision,
    features: AnalyzerFeatures,
) -> DecisionAuditRecord:
    confidence_context: list[str] = [f"confidence={decision['confidence']}"]
    if decision["confidence"] < 0.55:
        confidence_context.append("confidence_below_runtime_threshold")
    if features.evidence_coverage < 0.75:
        confidence_context.append("evidence_coverage_partial")
    if features.retrieval_conflict >= 1.0:
        confidence_context.append("retrieval_conflict_present")

    return DecisionAuditRecord(
        decision_id=str(decision["decision_id"]),
        packet_id=str(packet["packet_id"]),
        analyzer_family=str(decision["analyzer_family"]),
        severity_band=str(decision["severity_band"]),
        recommended_action=str(decision["recommended_action"]),
        needs_investigation=bool(decision["needs_investigation"]),
        investigation_trigger_reasons=tuple(decision["investigation_trigger_reasons"]),
        top_contributing_signals=_top_contributing_signals(features),
        ambiguity_flags=_ambiguity_flags(features),
        confidence_context=tuple(confidence_context),
        expected_value_hint=_investigation_value_hint(decision, features=features),
    )



def sidecar_assist_packet_payload(packet: SidecarAssistPacket) -> dict[str, object]:
    return {
        "packet_id": packet.packet_id,
        "service": packet.service,
        "operation": packet.operation,
        "suggested_query_terms": list(packet.suggested_query_terms),
        "ambiguity_flags": list(packet.ambiguity_flags),
        "investigation_value_hint": packet.investigation_value_hint,
        "notes": list(packet.notes),
    }



def decision_audit_record_payload(record: DecisionAuditRecord) -> dict[str, object]:
    return {
        "decision_id": record.decision_id,
        "packet_id": record.packet_id,
        "analyzer_family": record.analyzer_family,
        "severity_band": record.severity_band,
        "recommended_action": record.recommended_action,
        "needs_investigation": record.needs_investigation,
        "investigation_trigger_reasons": list(record.investigation_trigger_reasons),
        "top_contributing_signals": list(record.top_contributing_signals),
        "ambiguity_flags": list(record.ambiguity_flags),
        "confidence_context": list(record.confidence_context),
        "expected_value_hint": record.expected_value_hint,
    }
