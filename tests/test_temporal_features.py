from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.temporal_features import TemporalFeatureVector, extract_temporal_features
from app.packet.builder import build_incident_packet_v2_from_bundle, build_temporal_context_v2
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"


def _load_evidence_bundle() -> dict:
    with EVIDENCE_FIXTURE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_extract_temporal_features_builds_stable_signal_vector_from_packet_v2() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    packet = build_incident_packet_v2_from_bundle(
        normalized,
        _load_evidence_bundle(),
        temporal_context=build_temporal_context_v2(
            error_rate_1h=0.21,
            error_rate_24h=0.04,
            error_rate_7d_p95=0.06,
            latency_p95_1h=2400,
            latency_p95_24h=410,
            qps_1h=122,
            qps_24h=118,
            anomaly_duration_sec=900,
            deploy_age_sec=1200,
            rollback_recent=False,
            new_error_template_ratio=0.67,
        ),
    )

    features = extract_temporal_features(packet)

    assert features == TemporalFeatureVector(
        error_rate_regression=0.71,
        latency_regression=0.61,
        qps_shift=0.07,
        anomaly_persistence=0.25,
        deploy_recency=0.67,
        rollback_recency=0.0,
        template_churn=0.67,
    )


def test_extract_temporal_features_handles_missing_numeric_values_and_recent_rollback() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    packet = build_incident_packet_v2_from_bundle(
        normalized,
        _load_evidence_bundle(),
        temporal_context=build_temporal_context_v2(
            error_rate_1h=None,
            error_rate_24h=None,
            error_rate_7d_p95=None,
            latency_p95_1h=None,
            latency_p95_24h=None,
            qps_1h=None,
            qps_24h=None,
            anomaly_duration_sec=None,
            deploy_age_sec=None,
            rollback_recent=True,
            new_error_template_ratio=None,
        ),
    )

    features = extract_temporal_features(packet)

    assert features == TemporalFeatureVector(
        error_rate_regression=0.0,
        latency_regression=0.0,
        qps_shift=0.0,
        anomaly_persistence=0.0,
        deploy_recency=0.0,
        rollback_recency=1.0,
        template_churn=0.0,
    )
