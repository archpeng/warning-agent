"""Incident packet builder primitives for warning-agent packet-first baseline."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.packet.contracts import (
    EvidenceRefs,
    IncidentPacket,
    IncidentPacketV2,
    PacketHistory,
    PacketWindow,
    PrometheusEvidence,
    SignozEvidence,
    TemporalContextV2,
    TopologyEvidence,
)
from app.receiver.contracts import NormalizedAlertGroup

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug_component(value: str) -> str:
    return _NON_ALNUM.sub("_", value.lower()).strip("_")


def _timestamp_component(rfc3339_ts: str) -> str:
    dt = datetime.fromisoformat(rfc3339_ts.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%Y%m%dt%H%M%Sz")


def build_packet_id(service: str, operation: str | None, created_at: str) -> str:
    parts = [_slug_component(service)]
    if operation:
        parts.append(_slug_component(operation))
    else:
        parts.append("service")
    parts.append(_timestamp_component(created_at))
    return "ipk_" + "_".join(filter(None, parts))


def build_incident_packet(
    normalized_alert: NormalizedAlertGroup,
    *,
    created_at: str,
    window: PacketWindow,
    prometheus: PrometheusEvidence,
    signoz: SignozEvidence,
    topology: TopologyEvidence,
    evidence_refs: EvidenceRefs,
    history: PacketHistory | None = None,
) -> IncidentPacket:
    service = normalized_alert.get("service")
    if not service:
        raise ValueError("normalized alert must include service")

    environment = normalized_alert.get("environment") or "unknown"
    operation = normalized_alert.get("operation")
    entity_type = "service_operation" if operation else "service"
    entity_key = f"{service}:{operation}" if operation else service

    packet: IncidentPacket = {
        "schema_version": "incident-packet.v1",
        "packet_id": build_packet_id(service, operation, created_at),
        "candidate_source": normalized_alert["candidate_source"],
        "created_at": created_at,
        "environment": environment,
        "service": service,
        "operation": operation,
        "entity_type": entity_type,
        "entity_key": entity_key,
        "window": window,
        "prometheus": prometheus,
        "signoz": signoz,
        "topology": topology,
        "evidence_refs": evidence_refs,
    }
    if history is not None:
        packet["history"] = history
    return packet


def build_incident_packet_from_bundle(
    normalized_alert: NormalizedAlertGroup,
    evidence_bundle: dict[str, Any],
) -> IncidentPacket:
    return build_incident_packet(
        normalized_alert,
        created_at=evidence_bundle["created_at"],
        window=evidence_bundle["window"],
        prometheus=evidence_bundle["prometheus"],
        signoz=evidence_bundle["signoz"],
        topology=evidence_bundle["topology"],
        evidence_refs=evidence_bundle["evidence_refs"],
        history=evidence_bundle.get("history"),
    )


def build_temporal_context_v2(
    *,
    error_rate_1h: float | None,
    error_rate_24h: float | None,
    error_rate_7d_p95: float | None,
    latency_p95_1h: float | None,
    latency_p95_24h: float | None,
    qps_1h: float | None,
    qps_24h: float | None,
    anomaly_duration_sec: int | None,
    deploy_age_sec: int | None,
    rollback_recent: bool,
    new_error_template_ratio: float | None,
) -> TemporalContextV2:
    return {
        "error_rate_1h": error_rate_1h,
        "error_rate_24h": error_rate_24h,
        "error_rate_7d_p95": error_rate_7d_p95,
        "latency_p95_1h": latency_p95_1h,
        "latency_p95_24h": latency_p95_24h,
        "qps_1h": qps_1h,
        "qps_24h": qps_24h,
        "anomaly_duration_sec": anomaly_duration_sec,
        "deploy_age_sec": deploy_age_sec,
        "rollback_recent": rollback_recent,
        "new_error_template_ratio": new_error_template_ratio,
    }


def build_incident_packet_v2(packet: IncidentPacket, *, temporal_context: TemporalContextV2) -> IncidentPacketV2:
    upgraded: IncidentPacketV2 = {
        **packet,
        "schema_version": "incident-packet.v2",
        "temporal_context": temporal_context,
    }
    return upgraded



def build_incident_packet_v2_from_bundle(
    normalized_alert: NormalizedAlertGroup,
    evidence_bundle: dict[str, Any],
    *,
    temporal_context: TemporalContextV2,
) -> IncidentPacketV2:
    return build_incident_packet_v2(
        build_incident_packet_from_bundle(normalized_alert, evidence_bundle),
        temporal_context=temporal_context,
    )
