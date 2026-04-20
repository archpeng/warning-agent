"""Shared normalized alert contracts for receiver-facing runtime inputs."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from app.packet.contracts import CandidateSource


class NormalizedSourceRefs(TypedDict, total=False):
    rule_id: str | None
    source_url: str | None
    eval_window: str | None
    starts_at: str | None
    ends_at: str | None
    severity: str | None


class NormalizedAlertGroup(TypedDict):
    candidate_source: CandidateSource
    receiver: str
    status: str
    alert_count: int
    alertname: str | None
    environment: str | None
    service: str | None
    operation: str | None
    group_key: str
    common_labels: dict[str, str]
    common_annotations: dict[str, str]
    source_refs: NotRequired[NormalizedSourceRefs]
