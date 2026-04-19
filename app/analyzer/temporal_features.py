"""Temporal feature extraction over incident-packet.v2 surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from app.analyzer.base import clip_score, round_score
from app.packet.contracts import IncidentPacketV2, TemporalContextV2

TEMPORAL_FEATURE_SET_VERSION = "temporal-context-v2.features.v1"


@dataclass(frozen=True)
class TemporalFeatureVector:
    error_rate_regression: float
    latency_regression: float
    qps_shift: float
    anomaly_persistence: float
    deploy_recency: float
    rollback_recency: float
    template_churn: float


def _safe_float(value: float | int | None) -> float:
    return float(value) if value is not None else 0.0


def _error_rate_regression(context: TemporalContextV2) -> float:
    error_rate_1h = _safe_float(context.get("error_rate_1h"))
    error_rate_24h = _safe_float(context.get("error_rate_24h"))
    error_rate_7d_p95 = _safe_float(context.get("error_rate_7d_p95"))
    denominator = max(error_rate_24h, error_rate_7d_p95, 0.01)
    raw = max(0.0, error_rate_1h - error_rate_24h) / denominator / 4.0
    return round_score(raw)


def _latency_regression(context: TemporalContextV2) -> float:
    latency_p95_1h = _safe_float(context.get("latency_p95_1h"))
    latency_p95_24h = _safe_float(context.get("latency_p95_24h"))
    denominator = max(latency_p95_24h, 1.0)
    raw = max(0.0, latency_p95_1h - latency_p95_24h) / denominator / 8.0
    return round_score(raw)


def _qps_shift(context: TemporalContextV2) -> float:
    qps_1h = _safe_float(context.get("qps_1h"))
    qps_24h = _safe_float(context.get("qps_24h"))
    denominator = max(qps_24h, 1.0)
    raw = abs(qps_1h - qps_24h) / denominator * 2.0
    return round_score(raw)


def _anomaly_persistence(context: TemporalContextV2) -> float:
    duration = _safe_float(context.get("anomaly_duration_sec"))
    return round_score(duration / 3600.0)


def _deploy_recency(context: TemporalContextV2) -> float:
    deploy_age_sec = context.get("deploy_age_sec")
    if deploy_age_sec is None:
        return 0.0
    return round_score(clip_score(1.0 - (float(deploy_age_sec) / 3600.0)))


def extract_temporal_features(packet: IncidentPacketV2) -> TemporalFeatureVector:
    context = packet["temporal_context"]
    return TemporalFeatureVector(
        error_rate_regression=_error_rate_regression(context),
        latency_regression=_latency_regression(context),
        qps_shift=_qps_shift(context),
        anomaly_persistence=_anomaly_persistence(context),
        deploy_recency=_deploy_recency(context),
        rollback_recency=1.0 if context.get("rollback_recent") else 0.0,
        template_churn=round_score(_safe_float(context.get("new_error_template_ratio"))),
    )
