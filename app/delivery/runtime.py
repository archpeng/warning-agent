"""Durable local and env-gated live delivery adapter runtime for warning-agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

import yaml

from app.delivery.adapter_feishu import (
    build_adapter_feishu_notification_payload,
    serialize_adapter_feishu_notification_payload,
)
from app.delivery.env_gate import resolve_adapter_feishu_env_gate
from app.delivery.http_client import post_adapter_feishu_notification
from app.reports.contracts import DeliveryClass
from app.storage.artifact_store import JSONLArtifactStore


SCHEMA_VERSION: Final = "delivery-dispatch.v1"
LocalDurableAdapter = Literal["markdown_only", "local_ticket_queue", "local_page_queue", "local_review_queue"]
LiveVendorAdapter = Literal["adapter_feishu"]
DeliveryAdapter = LocalDurableAdapter | LiveVendorAdapter
DeliveryMode = Literal["local_durable", "env_gated_live"]
_VALID_DELIVERY_CLASSES: Final[set[str]] = {"observe", "open_ticket", "page_owner", "send_to_human_review"}
_LOCAL_DURABLE_ADAPTERS: Final[set[str]] = {
    "markdown_only",
    "local_ticket_queue",
    "local_page_queue",
    "local_review_queue",
}


@dataclass(frozen=True)
class LocalDurableRoute:
    delivery_class: DeliveryClass
    adapter: LocalDurableAdapter
    delivery_mode: Literal["local_durable"]
    queue: str


@dataclass(frozen=True)
class FeishuTargetEnvConfig:
    channel: Literal["feishu"]
    chat_id_env: str | None
    open_id_env: str | None
    thread_id_env: str | None


@dataclass(frozen=True)
class EnvGatedLiveRoute:
    delivery_class: DeliveryClass
    adapter: Literal["adapter_feishu"]
    delivery_mode: Literal["env_gated_live"]
    provider_key: Literal["warning-agent"]
    endpoint_env: str
    timeout_seconds: int
    target: FeishuTargetEnvConfig


DeliveryRoute = LocalDurableRoute | EnvGatedLiveRoute


@dataclass(frozen=True)
class DeliveryConfig:
    routes: dict[DeliveryClass, DeliveryRoute]


@dataclass(frozen=True)
class DeliveryDispatchResult:
    record: dict[str, object]
    dispatch_path: Path
    payload_path: Path
    bridge_payload_path: Path | None = None



def load_delivery_config(config_path: str | Path = Path("configs/delivery.yaml")) -> DeliveryConfig:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    raw_routes = payload.get("routes") or {}
    routes: dict[DeliveryClass, DeliveryRoute] = {}
    for delivery_class, route_payload in raw_routes.items():
        if delivery_class not in _VALID_DELIVERY_CLASSES:
            raise ValueError(f"unknown delivery class in config: {delivery_class}")
        if not isinstance(route_payload, dict):
            raise ValueError(f"delivery route payload must be a mapping: {delivery_class}")
        routes[cast(DeliveryClass, delivery_class)] = _load_route(
            cast(DeliveryClass, delivery_class),
            cast(dict[str, object], route_payload),
        )
    return DeliveryConfig(routes=routes)



def _load_route(delivery_class: DeliveryClass, route_payload: dict[str, object]) -> DeliveryRoute:
    delivery_mode = str(route_payload.get("delivery_mode") or "local_durable")
    if delivery_mode == "local_durable":
        return _load_local_durable_route(delivery_class, route_payload)
    if delivery_mode == "env_gated_live":
        return _load_env_gated_live_route(delivery_class, route_payload)
    raise ValueError(f"unknown delivery mode in config: {delivery_mode}")



def _load_local_durable_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> LocalDurableRoute:
    adapter = str(route_payload["adapter"])
    if adapter not in _LOCAL_DURABLE_ADAPTERS:
        raise ValueError(f"unknown local durable adapter in config: {adapter}")
    queue = str(route_payload["queue"])
    if not queue:
        raise ValueError(f"missing queue for local durable route: {delivery_class}")
    return LocalDurableRoute(
        delivery_class=delivery_class,
        adapter=cast(LocalDurableAdapter, adapter),
        delivery_mode="local_durable",
        queue=queue,
    )



def _load_env_gated_live_route(
    delivery_class: DeliveryClass,
    route_payload: dict[str, object],
) -> EnvGatedLiveRoute:
    if delivery_class != "page_owner":
        raise ValueError(f"env-gated live delivery only supported for page_owner: {delivery_class}")
    adapter = str(route_payload["adapter"])
    if adapter != "adapter_feishu":
        raise ValueError(f"unknown env-gated live adapter in config: {adapter}")
    provider_key = str(route_payload["provider_key"])
    if provider_key != "warning-agent":
        raise ValueError(f"unsupported provider key for adapter_feishu route: {provider_key}")
    endpoint_env = str(route_payload["endpoint_env"])
    timeout_seconds = int(route_payload["timeout_seconds"])
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    target_payload = route_payload.get("target") or {}
    if not isinstance(target_payload, dict):
        raise ValueError("env-gated live target payload must be a mapping")
    channel = str(target_payload.get("channel") or "")
    if channel != "feishu":
        raise ValueError(f"unsupported target channel for adapter_feishu route: {channel}")
    chat_id_env = target_payload.get("chat_id_env")
    open_id_env = target_payload.get("open_id_env")
    if not chat_id_env and not open_id_env:
        raise ValueError("adapter_feishu route requires chat_id_env or open_id_env")
    return EnvGatedLiveRoute(
        delivery_class=delivery_class,
        adapter="adapter_feishu",
        delivery_mode="env_gated_live",
        provider_key="warning-agent",
        endpoint_env=endpoint_env,
        timeout_seconds=timeout_seconds,
        target=FeishuTargetEnvConfig(
            channel="feishu",
            chat_id_env=str(chat_id_env) if chat_id_env else None,
            open_id_env=str(open_id_env) if open_id_env else None,
            thread_id_env=str(target_payload.get("thread_id_env")) if target_payload.get("thread_id_env") else None,
        ),
    )



def _build_dispatch_id(report_record: dict[str, object], delivery_class: str) -> str:
    report_id = str(report_record["report_id"])
    suffix = report_id[4:] if report_id.startswith("rpt_") else report_id
    return f"ddp_{suffix}_{delivery_class}"



def _payload_path(
    artifact_store: JSONLArtifactStore,
    *,
    bucket: str,
    dispatch_id: str,
    extension: str,
) -> Path:
    path = artifact_store.root / "deliveries" / bucket / f"{dispatch_id}.{extension}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path



def _persist_local_durable_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    route: LocalDurableRoute,
    dispatch_id: str,
) -> DeliveryDispatchResult:
    payload_path = _payload_path(artifact_store, bucket=route.queue, dispatch_id=dispatch_id, extension="md")
    payload_path.write_text(str(report_record["markdown"]), encoding="utf-8")
    record = {
        "schema_version": SCHEMA_VERSION,
        "dispatch_id": dispatch_id,
        "report_id": str(report_record["report_id"]),
        "packet_id": str(report_record["packet_id"]),
        "decision_id": str(report_record["decision_id"]),
        "delivery_class": route.delivery_class,
        "route_adapter": route.adapter,
        "delivery_mode": route.delivery_mode,
        "queue": route.queue,
        "status": "queued",
        "env_gate_state": None,
        "generated_at": str(report_record["generated_at"]),
        "payload_path": str(payload_path),
        "bridge_payload_path": None,
    }
    dispatch_path = artifact_store.append("deliveries", record)
    return DeliveryDispatchResult(record=record, dispatch_path=dispatch_path, payload_path=payload_path)



def _persist_env_gated_live_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    route: EnvGatedLiveRoute,
    dispatch_id: str,
) -> DeliveryDispatchResult:
    payload_path = _payload_path(
        artifact_store,
        bucket=str(route.delivery_class),
        dispatch_id=dispatch_id,
        extension="md",
    )
    payload_path.write_text(str(report_record["markdown"]), encoding="utf-8")

    resolution = resolve_adapter_feishu_env_gate(route)
    base_record = {
        "schema_version": SCHEMA_VERSION,
        "dispatch_id": dispatch_id,
        "report_id": str(report_record["report_id"]),
        "packet_id": str(report_record["packet_id"]),
        "decision_id": str(report_record["decision_id"]),
        "delivery_class": route.delivery_class,
        "route_adapter": route.adapter,
        "delivery_mode": route.delivery_mode,
        "provider_key": route.provider_key,
        "queue": None,
        "generated_at": str(report_record["generated_at"]),
        "payload_path": str(payload_path),
        "target_channel": route.target.channel,
    }

    if resolution.state != "ready" or resolution.target is None or resolution.endpoint is None:
        record = {
            **base_record,
            "status": "deferred",
            "env_gate_state": resolution.state,
            "missing_env": list(resolution.missing_env),
            "target_ref": None,
            "live_endpoint": resolution.endpoint,
            "bridge_payload_path": None,
        }
        dispatch_path = artifact_store.append("deliveries", record)
        return DeliveryDispatchResult(record=record, dispatch_path=dispatch_path, payload_path=payload_path)

    bridge_payload = serialize_adapter_feishu_notification_payload(
        build_adapter_feishu_notification_payload(report_record, target=resolution.target)
    )
    bridge_payload_path = _payload_path(
        artifact_store,
        bucket=route.adapter,
        dispatch_id=dispatch_id,
        extension="json",
    )
    bridge_payload_path.write_text(json.dumps(bridge_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    target_ref = resolution.target.chat_id or resolution.target.open_id
    live_endpoint = f"{resolution.endpoint}/providers/webhook"
    bridge_result = post_adapter_feishu_notification(
        endpoint=live_endpoint,
        payload=bridge_payload,
        timeout_seconds=route.timeout_seconds,
    )
    record = {
        **base_record,
        "status": bridge_result.status,
        "env_gate_state": resolution.state,
        "missing_env": [],
        "target_ref": target_ref,
        "live_endpoint": live_endpoint,
        "bridge_payload_path": str(bridge_payload_path),
        "response_code": bridge_result.response_code,
        "provider_key": bridge_result.provider_key,
        "provider_status": bridge_result.provider_status,
        "external_ref": bridge_result.external_ref,
        "error_message": bridge_result.message,
        "raw_response": bridge_result.raw_response,
    }
    dispatch_path = artifact_store.append("deliveries", record)
    return DeliveryDispatchResult(
        record=record,
        dispatch_path=dispatch_path,
        payload_path=payload_path,
        bridge_payload_path=bridge_payload_path,
    )



def persist_report_delivery(
    *,
    report_record: dict[str, object],
    artifact_store: JSONLArtifactStore,
    config_path: str | Path = Path("configs/delivery.yaml"),
) -> DeliveryDispatchResult:
    delivery_class = str(report_record["delivery_class"])
    config = load_delivery_config(config_path)
    route = config.routes.get(cast(DeliveryClass, delivery_class))
    if route is None:
        raise ValueError(f"missing delivery route for class: {delivery_class}")

    dispatch_id = _build_dispatch_id(report_record, delivery_class)
    if isinstance(route, LocalDurableRoute):
        return _persist_local_durable_delivery(
            report_record=report_record,
            artifact_store=artifact_store,
            route=route,
            dispatch_id=dispatch_id,
        )
    return _persist_env_gated_live_delivery(
        report_record=report_record,
        artifact_store=artifact_store,
        route=route,
        dispatch_id=dispatch_id,
    )
