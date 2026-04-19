"""SigNoz alert normalization surfaces for the Signoz-first warning plane."""

from __future__ import annotations

from typing import TypedDict

from app.receiver.alertmanager_webhook import NormalizedAlertGroup, NormalizedSourceRefs


class SignozAlertPayload(TypedDict, total=False):
    alertname: str
    alert: str
    state: str
    status: str
    ruleId: str
    rule_id: str
    serviceName: str
    service: str
    endpoint: str
    operation: str
    environment: str
    severity: str
    startsAt: str
    endsAt: str | None
    source: str
    evalWindow: str
    labels: dict[str, str]
    annotations: dict[str, str]


class SignozAlertRefs(TypedDict):
    rule_id: str | None
    source_url: str | None
    eval_window: str | None
    service: str | None
    endpoint: str | None
    severity: str | None


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_map(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(key, str) and isinstance(value, str)}


def extract_signoz_alert_refs(payload: SignozAlertPayload) -> SignozAlertRefs:
    labels = _string_map(payload.get("labels"))
    return {
        "rule_id": _first_non_empty(payload.get("ruleId"), payload.get("rule_id")),
        "source_url": _first_non_empty(payload.get("source")),
        "eval_window": _first_non_empty(payload.get("evalWindow")),
        "service": _first_non_empty(
            payload.get("serviceName"),
            payload.get("service"),
            labels.get("serviceName"),
            labels.get("service"),
        ),
        "endpoint": _first_non_empty(
            payload.get("endpoint"),
            payload.get("operation"),
            labels.get("endpoint"),
            labels.get("operation"),
        ),
        "severity": _first_non_empty(payload.get("severity"), labels.get("severity")),
    }


def _normalized_source_refs(refs: SignozAlertRefs) -> NormalizedSourceRefs:
    return {
        "rule_id": refs["rule_id"],
        "source_url": refs["source_url"],
        "eval_window": refs["eval_window"],
        "severity": refs["severity"],
    }


def normalize_signoz_alert_payload(payload: SignozAlertPayload) -> NormalizedAlertGroup:
    labels = _string_map(payload.get("labels"))
    annotations = _string_map(payload.get("annotations"))
    refs = extract_signoz_alert_refs(payload)

    alertname = _first_non_empty(payload.get("alertname"), payload.get("alert"), labels.get("alertname"))
    environment = _first_non_empty(payload.get("environment"), labels.get("environment"))
    service = refs["service"]
    operation = refs["endpoint"]

    common_labels = dict(labels)
    if alertname is not None:
        common_labels.setdefault("alertname", alertname)
    if service is not None:
        common_labels.setdefault("service", service)
    if operation is not None:
        common_labels.setdefault("operation", operation)
    if refs["severity"] is not None:
        common_labels.setdefault("severity", refs["severity"])

    group_parts = ["signoz", refs["rule_id"], service, operation]
    group_key = ":".join(part for part in group_parts if part) or "signoz"

    return {
        "candidate_source": "signoz_alert",
        "receiver": "signoz",
        "status": _first_non_empty(payload.get("state"), payload.get("status")) or "firing",
        "alert_count": 1,
        "alertname": alertname,
        "environment": environment,
        "service": service,
        "operation": operation,
        "group_key": group_key,
        "common_labels": common_labels,
        "common_annotations": annotations,
        "source_refs": _normalized_source_refs(refs),
    }
