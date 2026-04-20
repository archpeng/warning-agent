"""Runtime-facing trained scorer artifact loading and scoring surface."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict

from app.analyzer.base import (
    AnalyzerThresholds,
    build_decision_id,
    extract_features,
    load_thresholds,
    round_score,
    severity_band_from_score,
)
from app.analyzer.calibrate import decide_investigation
from app.analyzer.contracts import LocalAnalyzerDecision, RetrievalHit
from app.analyzer.fast_scorer import FastScorer
from app.analyzer.temporal_features import TemporalFeatureVector, extract_temporal_features
from app.analyzer.versioning import TRAINED_SCORER_ANALYZER_VERSION
from app.packet.builder import build_incident_packet_v2
from app.packet.contracts import IncidentPacket, IncidentPacketV2, TemporalContextV2

TRAINED_SCORER_ARTIFACT_VERSION: Final = "local-analyzer-trained-scorer.v1"
DEFAULT_TRAINED_SCORER_ARTIFACT_PATH: Final = Path("data/models/local-analyzer-trained-scorer.v1.json")
TRAINED_SCORER_MODEL_FAMILY: Final = "logistic_regression"
TRAINED_SCORER_CALIBRATION_METHOD: Final = "platt_scaling"


class CalibrationParameters(TypedDict):
    slope: float
    intercept: float


class TrainedScorerArtifact(TypedDict):
    artifact_version: str
    generated_at: str
    feature_set_version: str
    base_analyzer_version: str
    analyzer_version: str
    model_family: str
    calibration_method: str
    training_state: str
    feature_columns: list[str]
    training_case_count: int
    severe_case_count: int
    weights: list[float]
    bias: float
    calibration_parameters: CalibrationParameters


@dataclass(frozen=True)
class TrainedScorer:
    thresholds: AnalyzerThresholds
    weights: tuple[float, ...]
    bias: float
    calibration_slope: float
    calibration_intercept: float
    analyzer_version: str = TRAINED_SCORER_ANALYZER_VERSION

    @classmethod
    def from_artifact_path(
        cls,
        artifact_path: str | Path,
        *,
        thresholds: AnalyzerThresholds | None = None,
    ) -> "TrainedScorer":
        artifact = load_trained_scorer_artifact(artifact_path)
        if artifact["training_state"] != "ready":
            raise ValueError("trained scorer artifact must be ready before runtime integration")
        return cls(
            thresholds=thresholds or load_thresholds(),
            weights=tuple(float(value) for value in artifact["weights"]),
            bias=float(artifact["bias"]),
            calibration_slope=float(artifact["calibration_parameters"]["slope"]),
            calibration_intercept=float(artifact["calibration_parameters"]["intercept"]),
            analyzer_version=str(artifact["analyzer_version"]),
        )

    def predict_probability(self, packet: IncidentPacket | IncidentPacketV2) -> float:
        vector = _feature_vector(packet)
        raw_score = sum(weight * value for weight, value in zip(self.weights, vector, strict=True)) + self.bias
        calibrated = _sigmoid(self.calibration_slope * raw_score + self.calibration_intercept)
        return round_score(calibrated)

    def score_packet(
        self,
        packet: dict[str, object],
        *,
        retrieval_hits: list[RetrievalHit] | None = None,
    ) -> LocalAnalyzerDecision:
        retrieval_hits = retrieval_hits or []
        baseline = FastScorer(self.thresholds)
        baseline_decision = baseline.score_packet(packet, retrieval_hits=retrieval_hits)
        baseline_features = extract_features(packet, retrieval_hits)

        severity_score = max(self.predict_probability(packet), float(baseline_decision["severity_score"]))
        novelty_score = float(baseline_decision["novelty_score"])
        confidence = float(baseline_decision["confidence"])
        severity_band = severity_band_from_score(severity_score, self.thresholds)
        recommended_action = baseline._recommended_action(severity_band, baseline_features)
        needs_investigation, investigation_trigger_reasons = decide_investigation(
            baseline_features,
            novelty_score=novelty_score,
            confidence=confidence,
            recommended_action=recommended_action,
            severity_score=severity_score,
            thresholds=self.thresholds,
        )

        return {
            "schema_version": "local-analyzer-decision.v1",
            "decision_id": build_decision_id(packet),
            "packet_id": str(packet["packet_id"]),
            "analyzer_family": "hybrid",
            "analyzer_version": self.analyzer_version,
            "severity_band": severity_band,
            "severity_score": severity_score,
            "novelty_score": novelty_score,
            "confidence": confidence,
            "needs_investigation": needs_investigation,
            "recommended_action": recommended_action,
            "reason_codes": list(baseline_decision["reason_codes"]),
            "risk_flags": list(baseline_decision["risk_flags"]),
            "retrieval_hits": retrieval_hits,
            "investigation_trigger_reasons": investigation_trigger_reasons,
        }



def _sigmoid(value: float) -> float:
    if value >= 0:
        exp = math.exp(-value)
        return 1.0 / (1.0 + exp)
    exp = math.exp(value)
    return exp / (1.0 + exp)



def build_temporal_context_from_packet(packet: IncidentPacket) -> TemporalContextV2:
    prometheus = packet["prometheus"]
    signoz = packet["signoz"]
    history = packet.get("history", {})
    top_error_templates = signoz.get("top_error_templates") or []
    novelty_ratio = float(top_error_templates[0]["novelty_score"]) if top_error_templates else 0.0
    deploy_age_sec = 1800 if history.get("recent_deploy") else 21600

    return {
        "error_rate_1h": prometheus.get("error_rate"),
        "error_rate_24h": prometheus.get("error_rate_baseline"),
        "error_rate_7d_p95": _default_error_rate_p95(prometheus),
        "latency_p95_1h": prometheus.get("latency_p95_ms"),
        "latency_p95_24h": prometheus.get("latency_p95_baseline_ms"),
        "qps_1h": prometheus.get("qps"),
        "qps_24h": prometheus.get("qps_baseline"),
        "anomaly_duration_sec": int(packet["window"]["duration_sec"]),
        "deploy_age_sec": deploy_age_sec,
        "rollback_recent": False,
        "new_error_template_ratio": novelty_ratio,
    }



def ensure_packet_v2(packet: IncidentPacket | IncidentPacketV2) -> IncidentPacketV2:
    if packet.get("schema_version") == "incident-packet.v2" and "temporal_context" in packet:
        return packet  # type: ignore[return-value]
    return build_incident_packet_v2(packet, temporal_context=build_temporal_context_from_packet(packet))



def load_trained_scorer_artifact(path: str | Path) -> TrainedScorerArtifact:
    with Path(path).open("r", encoding="utf-8") as handle:
        artifact = json.load(handle)

    if artifact.get("artifact_version") != TRAINED_SCORER_ARTIFACT_VERSION:
        raise ValueError(f"unsupported trained scorer artifact version: {artifact.get('artifact_version')}")
    if artifact.get("weights") is None or artifact.get("bias") is None:
        raise ValueError("trained scorer artifact is missing fitted weights or bias")
    if artifact.get("calibration_parameters") is None:
        raise ValueError("trained scorer artifact is missing calibration parameters")
    return artifact



def _default_error_rate_p95(prometheus: dict[str, object]) -> float | None:
    baseline = prometheus.get("error_rate_baseline")
    current = prometheus.get("error_rate")
    if baseline is None and current is None:
        return None
    baseline_value = float(baseline or 0.0)
    current_value = float(current or 0.0)
    return max(baseline_value * 1.5, current_value * 0.3, 0.01)



def _feature_vector(packet: IncidentPacket | IncidentPacketV2) -> list[float]:
    temporal = extract_temporal_features(ensure_packet_v2(packet))
    return _vector_to_row(temporal)



def _vector_to_row(vector: TemporalFeatureVector) -> list[float]:
    return [
        float(vector.error_rate_regression),
        float(vector.latency_regression),
        float(vector.qps_shift),
        float(vector.anomaly_persistence),
        float(vector.deploy_recency),
        float(vector.rollback_recency),
        float(vector.template_churn),
    ]
