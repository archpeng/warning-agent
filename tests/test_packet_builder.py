from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.packet.builder import (
    build_incident_packet_from_bundle,
    build_incident_packet_v2_from_bundle,
    build_temporal_context_v2,
)
from app.packet.contracts import load_schema as load_packet_schema, load_v2_schema as load_packet_v2_schema
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.receiver.signoz_alert import normalize_signoz_alert_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"


def _load_evidence_bundle() -> dict:
    with EVIDENCE_FIXTURE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_packet_builder_produces_schema_valid_incident_packet() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(
        replay["alert_payload"],
        candidate_source="manual_replay",
    )
    packet = build_incident_packet_from_bundle(normalized, _load_evidence_bundle())

    validator = Draft202012Validator(load_packet_schema())
    errors = sorted(validator.iter_errors(packet), key=lambda error: error.json_path)

    assert not errors
    assert packet["packet_id"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert packet["entity_type"] == "service_operation"
    assert packet["entity_key"] == "checkout:POST /api/pay"


def test_packet_builder_freezes_schema_valid_incident_packet_v2_contract() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(
        replay["alert_payload"],
        candidate_source="manual_replay",
    )
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

    validator = Draft202012Validator(load_packet_v2_schema())
    errors = sorted(validator.iter_errors(packet), key=lambda error: error.json_path)

    assert not errors
    assert packet["schema_version"] == "incident-packet.v2"
    assert packet["packet_id"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert packet["temporal_context"] == {
        "error_rate_1h": 0.21,
        "error_rate_24h": 0.04,
        "error_rate_7d_p95": 0.06,
        "latency_p95_1h": 2400,
        "latency_p95_24h": 410,
        "qps_1h": 122,
        "qps_24h": 118,
        "anomaly_duration_sec": 900,
        "deploy_age_sec": 1200,
        "rollback_recent": False,
        "new_error_template_ratio": 0.67,
    }


def test_packet_builder_accepts_signoz_alert_candidate_source() -> None:
    normalized = normalize_signoz_alert_payload(
        {
            "alert": "signoz error",
            "state": "firing",
            "ruleId": "019d1fad-feb8-74c3-9610-dd894c6390d0",
            "serviceName": "prod-hq-bff-service",
            "endpoint": "POST /api/datamesh/v1/charts/data",
            "labels": {"environment": "prod", "severity": "error"},
            "annotations": {"summary": "current error rate crossed threshold"},
        }
    )
    packet = build_incident_packet_from_bundle(normalized, _load_evidence_bundle())

    validator = Draft202012Validator(load_packet_schema())
    errors = sorted(validator.iter_errors(packet), key=lambda error: error.json_path)

    assert not errors
    assert packet["candidate_source"] == "signoz_alert"
    assert packet["service"] == "prod-hq-bff-service"
    assert packet["operation"] == "POST /api/datamesh/v1/charts/data"
    assert packet["entity_type"] == "service_operation"
    assert packet["entity_key"] == "prod-hq-bff-service:POST /api/datamesh/v1/charts/data"
