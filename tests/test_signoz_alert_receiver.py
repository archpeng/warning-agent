from __future__ import annotations

from app.receiver.signoz_alert import (
    extract_signoz_alert_refs,
    missing_required_signoz_fields,
    normalize_signoz_alert_payload,
)



def _sample_signoz_alert_payload() -> dict[str, object]:
    return {
        "alert": "signoz error",
        "state": "firing",
        "ruleId": "019d1fad-feb8-74c3-9610-dd894c6390d0",
        "serviceName": "prod-hq-bff-service",
        "endpoint": "POST /api/datamesh/v1/charts/data",
        "severity": "error",
        "evalWindow": "5m0s",
        "startsAt": "2026-04-20T12:00:00Z",
        "endsAt": None,
        "source": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
        "labels": {
            "severity": "error",
            "environment": "prod",
        },
        "annotations": {
            "summary": "current error rate crossed threshold",
            "description": "error rate for prod-hq-bff-service POST is above threshold",
        },
    }



def test_extract_signoz_alert_refs_collects_primary_warning_metadata() -> None:
    refs = extract_signoz_alert_refs(_sample_signoz_alert_payload())

    assert refs == {
        "rule_id": "019d1fad-feb8-74c3-9610-dd894c6390d0",
        "source_url": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
        "eval_window": "5m0s",
        "starts_at": "2026-04-20T12:00:00Z",
        "ends_at": None,
        "service": "prod-hq-bff-service",
        "endpoint": "POST /api/datamesh/v1/charts/data",
        "severity": "error",
    }



def test_normalize_signoz_alert_payload_maps_to_normalized_alert_group() -> None:
    normalized = normalize_signoz_alert_payload(_sample_signoz_alert_payload())

    assert normalized == {
        "candidate_source": "signoz_alert",
        "receiver": "signoz",
        "status": "firing",
        "alert_count": 1,
        "alertname": "signoz error",
        "environment": "prod",
        "service": "prod-hq-bff-service",
        "operation": "POST /api/datamesh/v1/charts/data",
        "group_key": "signoz:019d1fad-feb8-74c3-9610-dd894c6390d0:prod-hq-bff-service:POST /api/datamesh/v1/charts/data",
        "common_labels": {
            "severity": "error",
            "environment": "prod",
            "alertname": "signoz error",
            "service": "prod-hq-bff-service",
            "operation": "POST /api/datamesh/v1/charts/data",
        },
        "common_annotations": {
            "summary": "current error rate crossed threshold",
            "description": "error rate for prod-hq-bff-service POST is above threshold",
        },
        "source_refs": {
            "rule_id": "019d1fad-feb8-74c3-9610-dd894c6390d0",
            "source_url": "http://signoz-prod.eshine.cn:32341/alerts/overview?ruleId=019d1fad-feb8-74c3-9610-dd894c6390d0",
            "eval_window": "5m0s",
            "starts_at": "2026-04-20T12:00:00Z",
            "ends_at": None,
            "severity": "error",
        },
    }



def test_missing_required_signoz_fields_surfaces_contract_gaps() -> None:
    missing = missing_required_signoz_fields({"state": "firing", "labels": {"environment": "prod"}})

    assert missing == ["alert", "ruleId", "serviceName", "endpoint"]
