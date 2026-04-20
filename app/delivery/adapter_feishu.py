"""Payload builders for the warning-agent -> adapter-feishu bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from app.delivery.env_gate import ResolvedFeishuTarget

AdapterFeishuSeverity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class AdapterFeishuFact:
    label: str
    value: str


@dataclass(frozen=True)
class AdapterFeishuTarget:
    channel: Literal["feishu"]
    chatId: str | None = None
    openId: str | None = None
    threadId: str | None = None


@dataclass(frozen=True)
class AdapterFeishuNotificationPayload:
    providerKey: Literal["warning-agent"]
    reportId: str
    runId: str
    summary: str
    title: str
    occurredAt: str
    severity: AdapterFeishuSeverity
    bodyMarkdown: str
    target: AdapterFeishuTarget
    facts: tuple[AdapterFeishuFact, ...]



def _build_adapter_feishu_title(report_record: Mapping[str, object]) -> str:
    severity_band = str(report_record["severity_band"])
    service = str(report_record["service"])
    operation = str(report_record.get("operation") or "").strip()
    if operation:
        return f"[{severity_band}] {service} {operation}"
    return f"[{severity_band}] {service}"



def _build_adapter_feishu_summary(report_record: Mapping[str, object]) -> str:
    service = str(report_record["service"])
    operation = str(report_record.get("operation") or "").strip()
    delivery_class = str(report_record["delivery_class"])
    investigation_stage = str(report_record["investigation_stage"])
    stage_phrase = {
        "none": "without investigation escalation",
        "local_primary": "after local_primary investigation",
        "cloud_fallback": "after cloud_fallback investigation",
    }.get(investigation_stage, f"after {investigation_stage} investigation")
    if operation:
        return f"{service} {operation} requires {delivery_class} {stage_phrase}"
    return f"{service} requires {delivery_class} {stage_phrase}"



def _map_severity_band(severity_band: str) -> AdapterFeishuSeverity:
    if severity_band == "P1":
        return "critical"
    if severity_band == "P2":
        return "warning"
    return "info"



def _build_adapter_feishu_facts(report_record: Mapping[str, object]) -> tuple[AdapterFeishuFact, ...]:
    facts: list[AdapterFeishuFact] = [
        AdapterFeishuFact(label="service", value=str(report_record["service"])),
    ]
    operation = str(report_record.get("operation") or "").strip()
    if operation:
        facts.append(AdapterFeishuFact(label="operation", value=operation))
    facts.append(AdapterFeishuFact(label="delivery_class", value=str(report_record["delivery_class"])))
    facts.append(AdapterFeishuFact(label="investigation_stage", value=str(report_record["investigation_stage"])))
    owner = str(report_record.get("owner") or "").strip()
    if owner:
        facts.append(AdapterFeishuFact(label="owner", value=owner))
    return tuple(facts)



def build_adapter_feishu_notification_payload(
    report_record: Mapping[str, object],
    *,
    target: ResolvedFeishuTarget,
) -> AdapterFeishuNotificationPayload:
    return AdapterFeishuNotificationPayload(
        providerKey="warning-agent",
        reportId=str(report_record["report_id"]),
        runId=str(report_record["packet_id"]),
        summary=_build_adapter_feishu_summary(report_record),
        title=_build_adapter_feishu_title(report_record),
        occurredAt=str(report_record["generated_at"]),
        severity=_map_severity_band(str(report_record["severity_band"])),
        bodyMarkdown=str(report_record["markdown"]),
        target=AdapterFeishuTarget(
            channel="feishu",
            chatId=target.chat_id,
            openId=target.open_id,
            threadId=target.thread_id,
        ),
        facts=_build_adapter_feishu_facts(report_record),
    )



def serialize_adapter_feishu_notification_payload(
    payload: AdapterFeishuNotificationPayload,
) -> dict[str, object]:
    target: dict[str, object] = {"channel": payload.target.channel}
    if payload.target.chatId:
        target["chatId"] = payload.target.chatId
    if payload.target.openId:
        target["openId"] = payload.target.openId
    if payload.target.threadId:
        target["threadId"] = payload.target.threadId

    return {
        "providerKey": payload.providerKey,
        "reportId": payload.reportId,
        "runId": payload.runId,
        "summary": payload.summary,
        "title": payload.title,
        "occurredAt": payload.occurredAt,
        "severity": payload.severity,
        "bodyMarkdown": payload.bodyMarkdown,
        "target": target,
        "facts": [{"label": fact.label, "value": fact.value} for fact in payload.facts],
    }
