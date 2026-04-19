"""Manual replay fixture loader for alert-driven bootstrap and shadow development."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal, TypedDict

MANUAL_REPLAY_PROTOCOL_VERSION: Final = "manual-replay.v1"


class AlertmanagerAlert(TypedDict):
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: str
    endsAt: str
    generatorURL: str
    fingerprint: str


class AlertmanagerWebhookPayload(TypedDict):
    receiver: str
    status: str
    alerts: list[AlertmanagerAlert]
    groupLabels: dict[str, str]
    commonLabels: dict[str, str]
    commonAnnotations: dict[str, str]
    externalURL: str
    version: str
    groupKey: str
    truncatedAlerts: int


class ManualReplayEnvelope(TypedDict):
    protocol_version: str
    candidate_source: Literal["manual_replay"]
    environment: str
    replay_label: str
    alert_payload: AlertmanagerWebhookPayload


def load_manual_replay_fixture(path: str | Path) -> ManualReplayEnvelope:
    fixture_path = Path(path)
    with fixture_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    required = {
        "protocol_version",
        "candidate_source",
        "environment",
        "replay_label",
        "alert_payload",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"manual replay fixture missing keys: {sorted(missing)}")

    if payload["protocol_version"] != MANUAL_REPLAY_PROTOCOL_VERSION:
        raise ValueError(
            f"unsupported replay protocol: {payload['protocol_version']} != {MANUAL_REPLAY_PROTOCOL_VERSION}"
        )

    if payload["candidate_source"] != "manual_replay":
        raise ValueError("manual replay fixture must use candidate_source=manual_replay")

    if not payload["alert_payload"].get("alerts"):
        raise ValueError("manual replay fixture must contain at least one alert")

    return payload


def summarize_manual_replay(envelope: ManualReplayEnvelope) -> dict[str, object]:
    payload = envelope["alert_payload"]
    common_labels = payload.get("commonLabels", {})
    return {
        "candidate_source": envelope["candidate_source"],
        "environment": envelope["environment"],
        "replay_label": envelope["replay_label"],
        "receiver": payload["receiver"],
        "status": payload["status"],
        "alert_count": len(payload["alerts"]),
        "service": common_labels.get("service"),
        "alertname": common_labels.get("alertname"),
    }
