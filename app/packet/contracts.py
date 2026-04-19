"""Base contract surface for incident packet artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from app.contracts_common import DATA_DIR, load_json_schema, schema_path

SCHEMA_VERSION: Final = "incident-packet.v1"
SCHEMA_FILE: Final = "incident-packet.v1.json"
SCHEMA_PATH: Final[Path] = schema_path(SCHEMA_FILE)
SCHEMA_VERSION_V2: Final = "incident-packet.v2"
SCHEMA_FILE_V2: Final = "incident-packet.v2.json"
SCHEMA_PATH_V2: Final[Path] = schema_path(SCHEMA_FILE_V2)
ARTIFACT_DIR: Final[Path] = DATA_DIR / "packets"

CandidateSource = Literal["alertmanager_webhook", "prometheus_scan", "manual_replay", "signoz_alert"]
EntityType = Literal["service", "service_operation"]
Tier = Literal["tier0", "tier1", "tier2", "unknown"]


class PacketWindow(TypedDict):
    start_ts: str
    end_ts: str
    duration_sec: int


class PrometheusEvidence(TypedDict):
    alerts_firing: list[str]
    error_rate: float | None
    error_rate_baseline: float | None
    error_rate_delta: float | None
    latency_p95_ms: float | None
    latency_p95_baseline_ms: float | None
    latency_p95_delta: float | None
    qps: float | None
    qps_baseline: float | None
    qps_delta: float | None
    saturation: float | None


class ErrorTemplate(TypedDict):
    template_id: str
    template: str
    count: int
    novelty_score: float


class SlowOperation(TypedDict):
    operation: str
    p95_ms: float
    error_ratio: float | None


class SignozAlertContext(TypedDict):
    rule_id: str | None
    source_url: str | None
    eval_window: str | None
    severity: str | None


class TraceDetailHint(TypedDict):
    trace_id: str
    span_name: str | None
    service_name: str | None
    target: str | None
    status_code: str | None


class SignozEvidence(TypedDict):
    top_error_templates: list[ErrorTemplate]
    top_slow_operations: list[SlowOperation]
    trace_error_ratio: float | None
    sample_trace_ids: list[str]
    sample_log_refs: list[str]
    alert_context: NotRequired[SignozAlertContext]
    trace_detail_hints: NotRequired[list[TraceDetailHint]]


class TopologyEvidence(TypedDict):
    tier: Tier
    owner: str | None
    repo_candidates: list[str]
    upstream_count: int
    downstream_count: int
    blast_radius_score: float


class PacketHistory(TypedDict, total=False):
    recent_deploy: bool
    similar_incident_ids: list[str]
    similar_packet_ids: list[str]


class TemporalContextV2(TypedDict):
    error_rate_1h: float | None
    error_rate_24h: float | None
    error_rate_7d_p95: float | None
    latency_p95_1h: float | None
    latency_p95_24h: float | None
    qps_1h: float | None
    qps_24h: float | None
    anomaly_duration_sec: int | None
    deploy_age_sec: int | None
    rollback_recent: bool
    new_error_template_ratio: float | None


class EvidenceRefs(TypedDict):
    prometheus_query_refs: list[str]
    signoz_query_refs: list[str]


class IncidentPacket(TypedDict):
    schema_version: str
    packet_id: str
    candidate_source: CandidateSource
    created_at: str
    environment: str
    service: str
    operation: str | None
    entity_type: EntityType
    entity_key: str
    window: PacketWindow
    prometheus: PrometheusEvidence
    signoz: SignozEvidence
    topology: TopologyEvidence
    history: NotRequired[PacketHistory]
    evidence_refs: EvidenceRefs


class IncidentPacketV2(IncidentPacket):
    temporal_context: TemporalContextV2


def load_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE)


def load_v2_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE_V2)
