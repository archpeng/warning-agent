"""Durable local delivery adapter runtime for warning-agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

import yaml

from app.reports.contracts import DeliveryClass
from app.storage.artifact_store import JSONLArtifactStore


SCHEMA_VERSION: Final = "delivery-dispatch.v1"
DeliveryAdapter = Literal["markdown_only", "local_ticket_queue", "local_page_queue", "local_review_queue"]
_VALID_DELIVERY_CLASSES: Final[set[str]] = {"observe", "open_ticket", "page_owner", "send_to_human_review"}


@dataclass(frozen=True)
class DeliveryRoute:
    delivery_class: DeliveryClass
    adapter: DeliveryAdapter
    queue: str


@dataclass(frozen=True)
class DeliveryConfig:
    routes: dict[DeliveryClass, DeliveryRoute]


@dataclass(frozen=True)
class DeliveryDispatchResult:
    record: dict[str, object]
    dispatch_path: Path
    payload_path: Path



def load_delivery_config(config_path: str | Path = Path("configs/delivery.yaml")) -> DeliveryConfig:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    raw_routes = payload.get("routes") or {}
    routes: dict[DeliveryClass, DeliveryRoute] = {}
    for delivery_class, route_payload in raw_routes.items():
        if delivery_class not in _VALID_DELIVERY_CLASSES:
            raise ValueError(f"unknown delivery class in config: {delivery_class}")
        routes[cast(DeliveryClass, delivery_class)] = DeliveryRoute(
            delivery_class=cast(DeliveryClass, delivery_class),
            adapter=cast(DeliveryAdapter, str(route_payload["adapter"])),
            queue=str(route_payload["queue"]),
        )
    return DeliveryConfig(routes=routes)



def _build_dispatch_id(report_record: dict[str, object], delivery_class: str) -> str:
    report_id = str(report_record["report_id"])
    suffix = report_id[4:] if report_id.startswith("rpt_") else report_id
    return f"ddp_{suffix}_{delivery_class}"



def _payload_path(artifact_store: JSONLArtifactStore, *, queue: str, dispatch_id: str) -> Path:
    path = artifact_store.root / "deliveries" / queue / f"{dispatch_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path



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
    payload_path = _payload_path(artifact_store, queue=route.queue, dispatch_id=dispatch_id)
    payload_path.write_text(str(report_record["markdown"]), encoding="utf-8")

    record = {
        "schema_version": SCHEMA_VERSION,
        "dispatch_id": dispatch_id,
        "report_id": str(report_record["report_id"]),
        "packet_id": str(report_record["packet_id"]),
        "decision_id": str(report_record["decision_id"]),
        "delivery_class": delivery_class,
        "route_adapter": route.adapter,
        "queue": route.queue,
        "status": "queued",
        "generated_at": str(report_record["generated_at"]),
        "payload_path": str(payload_path),
    }
    dispatch_path = artifact_store.append("deliveries", record)
    return DeliveryDispatchResult(record=record, dispatch_path=dispatch_path, payload_path=payload_path)
