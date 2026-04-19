"""Deterministic first-pass fast scorer baseline."""

from __future__ import annotations

from dataclasses import dataclass

from app.analyzer.base import (
    AnalyzerFeatures,
    AnalyzerThresholds,
    build_decision_id,
    extract_features,
    load_thresholds,
    round_score,
    severity_band_from_score,
)
from app.analyzer.calibrate import decide_investigation
from app.analyzer.contracts import LocalAnalyzerDecision, RetrievalHit
from app.analyzer.versioning import FAST_SCORER_ANALYZER_VERSION


@dataclass(frozen=True)
class FastScorer:
    thresholds: AnalyzerThresholds
    analyzer_version: str = FAST_SCORER_ANALYZER_VERSION

    @classmethod
    def from_config(cls) -> "FastScorer":
        return cls(thresholds=load_thresholds())

    def score_packet(
        self,
        packet: dict[str, object],
        *,
        retrieval_hits: list[RetrievalHit] | None = None,
    ) -> LocalAnalyzerDecision:
        retrieval_hits = retrieval_hits or []
        features = extract_features(packet, retrieval_hits)
        severity_score = self._severity_score(features)
        novelty_score = self._novelty_score(features)
        confidence = self._confidence(features, novelty_score)
        severity_band = severity_band_from_score(severity_score, self.thresholds)
        recommended_action = self._recommended_action(severity_band, features)
        reason_codes = self._reason_codes(features, novelty_score)
        risk_flags = self._risk_flags(features, novelty_score)
        needs_investigation, investigation_trigger_reasons = decide_investigation(
            features,
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
            "analyzer_family": "fast_scorer",
            "analyzer_version": self.analyzer_version,
            "severity_band": severity_band,
            "severity_score": severity_score,
            "novelty_score": novelty_score,
            "confidence": confidence,
            "needs_investigation": needs_investigation,
            "recommended_action": recommended_action,
            "reason_codes": reason_codes,
            "risk_flags": risk_flags,
            "retrieval_hits": retrieval_hits,
            "investigation_trigger_reasons": investigation_trigger_reasons,
        }

    @staticmethod
    def _severity_score(features: AnalyzerFeatures) -> float:
        score = (
            0.28 * features.error_rate_spike
            + 0.19 * features.latency_spike
            + 0.08 * features.trace_error_ratio
            + 0.19 * features.blast_radius_score
            + 0.11 * features.novelty_signal
            + 0.12 * features.severe_retrieval_similarity
            + 0.05 * features.alert_density
            + 0.04 * features.recent_deploy
        )
        return round_score(score)

    @staticmethod
    def _novelty_score(features: AnalyzerFeatures) -> float:
        score = features.novelty_signal - 0.05 * features.severe_retrieval_similarity
        return round_score(score)

    @staticmethod
    def _confidence(features: AnalyzerFeatures, novelty_score: float) -> float:
        score = (
            0.32
            + 0.18 * features.evidence_coverage
            + 0.08 * features.alert_density
            + 0.07 * features.severe_retrieval_similarity
            + 0.02 * features.recent_deploy
            - 0.05 * novelty_score
        )
        return round_score(score)

    def _recommended_action(self, severity_band: str, features: AnalyzerFeatures) -> str:
        if severity_band == "P1":
            return "page_owner"
        if severity_band == "P2":
            return "page_owner" if features.blast_radius_score >= 0.8 else "open_ticket"
        if severity_band == "P3":
            return "open_ticket"
        return "observe"

    def _reason_codes(self, features: AnalyzerFeatures, novelty_score: float) -> list[str]:
        reason_codes: list[str] = []
        if features.signoz_alert_signal >= 0.9:
            reason_codes.append("signoz_alert_firing")
        if features.error_rate_spike >= 0.75:
            reason_codes.append("error_rate_spike")
        if features.trace_error_ratio >= 0.6:
            reason_codes.append("trace_error_ratio_high")
        if features.latency_spike >= 0.6 and features.signoz_alert_signal >= 0.5:
            reason_codes.append("top_operation_latency_high")
        if novelty_score >= self.thresholds.novelty_threshold:
            reason_codes.append("template_novelty_high")
        if features.severe_retrieval_similarity >= 0.75:
            reason_codes.append("similar_to_past_severe")
        if features.owner_unknown >= 1.0:
            reason_codes.append("owner_unknown")
        if not reason_codes:
            reason_codes.append("baseline_triage")
        return reason_codes[:8]

    @staticmethod
    def _risk_flags(features: AnalyzerFeatures, novelty_score: float) -> list[str]:
        risk_flags: list[str] = []
        if features.blast_radius_score >= 0.7:
            risk_flags.append("high_blast_radius")
        if features.recent_deploy >= 1.0:
            risk_flags.append("recent_deploy")
        if features.owner_unknown >= 1.0:
            risk_flags.append("owner_unknown")
        if novelty_score >= 0.85 and features.severe_retrieval_similarity < 0.5:
            risk_flags.append("new_template")
        return risk_flags

def score_packet(
    packet: dict[str, object],
    *,
    retrieval_hits: list[RetrievalHit] | None = None,
) -> LocalAnalyzerDecision:
    return FastScorer.from_config().score_packet(packet, retrieval_hits=retrieval_hits)
