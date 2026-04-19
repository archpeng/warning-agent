"""Shared local-analyzer feature and threshold primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

import yaml

from app.analyzer.contracts import RetrievalHit


@dataclass(frozen=True)
class AnalyzerThresholds:
    severity_thresholds: dict[str, float]
    novelty_threshold: float
    investigation_threshold: float
    confidence_threshold: float
    blast_radius_threshold: float
    minimum_calibration_cases: int
    minimum_severe_cases: int
    false_page_ceiling: float


@dataclass(frozen=True)
class AnalyzerFeatures:
    error_rate_spike: float
    latency_spike: float
    trace_error_ratio: float
    blast_radius_score: float
    novelty_signal: float
    severe_retrieval_similarity: float
    benign_retrieval_similarity: float
    alert_density: float
    evidence_coverage: float
    recent_deploy: float
    owner_unknown: float
    retrieval_conflict: float
    signoz_alert_signal: float


def clip_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def round_score(value: float) -> float:
    return round(clip_score(value), 2)


def load_thresholds(config_path: str | Path = Path("configs/thresholds.yaml")) -> AnalyzerThresholds:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return AnalyzerThresholds(
        severity_thresholds=payload["severity_thresholds"],
        novelty_threshold=float(payload["novelty_threshold"]),
        investigation_threshold=float(payload["investigation_threshold"]),
        confidence_threshold=float(payload["confidence_threshold"]),
        blast_radius_threshold=float(payload["blast_radius_threshold"]),
        minimum_calibration_cases=int(payload["minimum_calibration_cases"]),
        minimum_severe_cases=int(payload["minimum_severe_cases"]),
        false_page_ceiling=float(payload["false_page_ceiling"]),
    )


def build_decision_id(packet: dict[str, object], *, offset_seconds: int = 2) -> str:
    created_at = str(packet["created_at"])
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC) + timedelta(
        seconds=offset_seconds
    )
    timestamp = dt.strftime("%Y%m%dt%H%M%Sz")
    service = str(packet["service"]).lower().replace("-", "_")
    operation = str(packet.get("operation") or "service").lower()
    operation = (
        operation.replace("/api/", "/")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
    operation = "_".join(part for part in operation.split("_") if part)
    return f"lad_{service}_{operation}_{timestamp}"


def severity_band_from_score(score: float, thresholds: AnalyzerThresholds) -> str:
    ordered = sorted(thresholds.severity_thresholds.items(), key=lambda item: item[1], reverse=True)
    for band, threshold in ordered:
        if score >= threshold:
            return band
    return ordered[-1][0]


def max_similarity(retrieval_hits: Iterable[RetrievalHit], known_outcome: str) -> float:
    values = [float(hit["similarity"]) for hit in retrieval_hits if hit["known_outcome"] == known_outcome]
    return max(values, default=0.0)


def _signoz_alert_signal(packet: dict[str, object], signoz: dict[str, object]) -> float:
    alert_context = signoz.get("alert_context") or {}
    if not isinstance(alert_context, dict):
        alert_context = {}

    severity = str(alert_context.get("severity") or "").lower()
    if severity in {"critical", "error", "high"}:
        return 1.0
    if severity in {"warning", "warn", "medium"}:
        return 0.7
    if severity:
        return 0.5
    if packet.get("candidate_source") == "signoz_alert":
        return 0.9
    return 0.0


def extract_features(packet: dict[str, object], retrieval_hits: list[RetrievalHit]) -> AnalyzerFeatures:
    prometheus = packet["prometheus"]
    signoz = packet["signoz"]
    topology = packet["topology"]
    history = packet.get("history", {})

    error_rate_delta = float(prometheus.get("error_rate_delta") or 0.0)
    latency_delta = float(prometheus.get("latency_p95_delta") or 0.0)
    trace_error_ratio = float(signoz.get("trace_error_ratio") or 0.0)
    top_operations = signoz.get("top_slow_operations") or []
    top_operation_error_ratio = max(
        (float(row.get("error_ratio") or 0.0) for row in top_operations if isinstance(row, dict)),
        default=0.0,
    )
    top_operation_latency_ms = max(
        (float(row.get("p95_ms") or 0.0) for row in top_operations if isinstance(row, dict)),
        default=0.0,
    )
    signoz_alert_signal = _signoz_alert_signal(packet, signoz)
    blast_radius_score = float(topology.get("blast_radius_score") or 0.0)
    novelty_signal = float(signoz["top_error_templates"][0]["novelty_score"])
    severe_retrieval_similarity = max_similarity(retrieval_hits, "severe")
    benign_retrieval_similarity = max_similarity(retrieval_hits, "benign")
    alerts_firing = list(prometheus.get("alerts_firing") or [])
    metrics_present = [
        prometheus.get("error_rate_delta"),
        prometheus.get("latency_p95_delta"),
        prometheus.get("qps_delta"),
        prometheus.get("saturation"),
        signoz.get("trace_error_ratio"),
        signoz.get("top_error_templates"),
        signoz.get("top_slow_operations"),
    ]
    if signoz_alert_signal > 0.0:
        metrics_present.append(signoz.get("alert_context"))
    trace_detail_hints = signoz.get("trace_detail_hints")
    if trace_detail_hints not in (None, []):
        metrics_present.append(trace_detail_hints)
    evidence_coverage = sum(value is not None and value != [] for value in metrics_present) / len(metrics_present)
    alert_sources = len(alerts_firing) + int(signoz_alert_signal > 0.0)

    return AnalyzerFeatures(
        error_rate_spike=clip_score(
            max(
                error_rate_delta / 0.2,
                trace_error_ratio,
                top_operation_error_ratio,
                signoz_alert_signal,
            )
        ),
        latency_spike=clip_score(max(latency_delta / 2000.0, top_operation_latency_ms / 3000.0)),
        trace_error_ratio=clip_score(max(trace_error_ratio, top_operation_error_ratio)),
        blast_radius_score=clip_score(blast_radius_score),
        novelty_signal=clip_score(novelty_signal),
        severe_retrieval_similarity=clip_score(severe_retrieval_similarity),
        benign_retrieval_similarity=clip_score(benign_retrieval_similarity),
        alert_density=clip_score(alert_sources / 2.0),
        evidence_coverage=clip_score(evidence_coverage),
        recent_deploy=1.0 if history.get("recent_deploy") else 0.0,
        owner_unknown=1.0 if topology.get("owner") in (None, "") else 0.0,
        retrieval_conflict=1.0 if severe_retrieval_similarity >= 0.6 and benign_retrieval_similarity >= 0.6 else 0.0,
        signoz_alert_signal=clip_score(signoz_alert_signal),
    )
