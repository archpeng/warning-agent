"""Minimal Alertmanager webhook stub and normalization surface for warning-agent."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict
import os
from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.collectors.evidence_bundle import build_live_evidence_bundle
from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector
from app.integration_evidence import build_integration_baseline
from app.packet.contracts import CandidateSource
from app.receiver.replay_loader import AlertmanagerWebhookPayload
from app.retrieval.index import RetrievalIndex
from app.storage.sqlite_store import MetadataStore

WEBHOOK_PATH: Final = "/webhook/alertmanager"
HEALTH_PATH: Final = "/healthz"
READINESS_PATH: Final = "/readyz"
WEBHOOK_RECEIPT_SCHEMA_VERSION: Final = "alertmanager-webhook-receipt.v1"


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


class WebhookRuntimeSummary(TypedDict):
    packet_id: str
    decision_id: str
    investigation_id: str | None
    investigation_stage: Literal["none", "local_primary", "cloud_fallback"]
    report_id: str
    rollout_evidence_path: str | None


class WebhookError(TypedDict):
    code: str
    message: str


class WebhookHealth(TypedDict):
    status: str
    service: str
    surface: str


class WebhookReadiness(TypedDict):
    status: str
    service: str
    surface: str
    evidence_source: Literal["fixture", "live"]
    checks: dict[str, bool]
    integration_baseline: dict[str, object]


class WebhookReceipt(TypedDict):
    schema_version: str
    accepted: bool
    receipt_state: Literal["accepted", "rejected"]
    normalized: NormalizedAlertGroup
    runtime: NotRequired[WebhookRuntimeSummary]
    error: NotRequired[WebhookError]


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def normalize_alertmanager_payload(
    payload: AlertmanagerWebhookPayload,
    *,
    candidate_source: Literal["alertmanager_webhook", "manual_replay"] = "alertmanager_webhook",
) -> NormalizedAlertGroup:
    alerts = payload.get("alerts", [])
    first_alert = alerts[0] if alerts else None
    common_labels = payload.get("commonLabels", {})
    group_labels = payload.get("groupLabels", {})
    first_labels = first_alert.get("labels", {}) if first_alert else {}

    return {
        "candidate_source": candidate_source,
        "receiver": payload["receiver"],
        "status": payload["status"],
        "alert_count": len(alerts),
        "alertname": _first_non_empty(
            common_labels.get("alertname"),
            group_labels.get("alertname"),
            first_labels.get("alertname"),
        ),
        "environment": _first_non_empty(
            common_labels.get("environment"),
            first_labels.get("environment"),
        ),
        "service": _first_non_empty(
            common_labels.get("service"),
            group_labels.get("service"),
            first_labels.get("service"),
        ),
        "operation": _first_non_empty(
            common_labels.get("operation"),
            first_labels.get("operation"),
        ),
        "group_key": payload["groupKey"],
        "common_labels": common_labels,
        "common_annotations": payload.get("commonAnnotations", {}),
    }


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_evidence_fixture(normalized: NormalizedAlertGroup, *, repo_root: Path) -> Path:
    service = normalized.get("service")
    if not service:
        raise ValueError("normalized alert must include service before webhook runtime execution")

    evidence_fixture = (repo_root / "fixtures" / "evidence" / f"{service}.packet-input.json").resolve()
    if not evidence_fixture.exists():
        raise ValueError(f"webhook evidence fixture does not exist: {evidence_fixture}")
    return evidence_fixture


def _build_health_payload() -> WebhookHealth:
    return {
        "status": "ok",
        "service": "warning-agent",
        "surface": "alertmanager_webhook",
    }



def _build_readiness_payload(
    *,
    repo_root: Path,
    data_root: str | Path | None,
    evidence_source: Literal["fixture", "live"],
) -> WebhookReadiness:
    checks = {
        "repo_root_exists": repo_root.exists(),
        "thresholds_config_exists": (repo_root / "configs" / "thresholds.yaml").exists(),
        "escalation_config_exists": (repo_root / "configs" / "escalation.yaml").exists(),
    }
    return {
        "status": "ready" if all(checks.values()) else "not_ready",
        "service": "warning-agent",
        "surface": "alertmanager_webhook",
        "evidence_source": evidence_source,
        "checks": checks,
        "integration_baseline": build_integration_baseline(repo_root=repo_root, data_root=data_root),
    }



def build_webhook_error_receipt(
    normalized: NormalizedAlertGroup,
    *,
    code: str,
    message: str,
) -> WebhookReceipt:
    return {
        "schema_version": WEBHOOK_RECEIPT_SCHEMA_VERSION,
        "accepted": False,
        "receipt_state": "rejected",
        "normalized": normalized,
        "error": {
            "code": code,
            "message": message,
        },
    }



def create_app(
    *,
    repo_root: str | Path = Path("."),
    data_root: str | Path | None = None,
    evidence_source: Literal["fixture", "live"] = "fixture",
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> FastAPI:
    from app.investigator.local_primary import prewarm_local_primary_resident_service

    repo_root = Path(repo_root)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        prewarm_local_primary_resident_service(
            config_path=repo_root / "configs" / "escalation.yaml",
            repo_root=repo_root,
            prewarm_source="fastapi_startup",
        )
        yield

    app = FastAPI(title="warning-agent governed warning ingress", lifespan=lifespan)

    @app.get(HEALTH_PATH)
    def healthz() -> WebhookHealth:
        return _build_health_payload()

    @app.get(READINESS_PATH, response_model=None)
    def readyz():
        readiness = _build_readiness_payload(
            repo_root=repo_root,
            data_root=data_root,
            evidence_source=evidence_source,
        )
        if readiness["status"] == "ready":
            return readiness
        return JSONResponse(status_code=503, content=readiness)

    @app.post(WEBHOOK_PATH, response_model=None)
    def receive_alertmanager_webhook(payload: AlertmanagerWebhookPayload):
        try:
            return build_webhook_receipt(
                payload,
                repo_root=repo_root,
                data_root=data_root,
                evidence_source=evidence_source,
                prometheus_collector=prometheus_collector,
                signoz_collector=signoz_collector,
                evidence_now=evidence_now,
            )
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content=build_webhook_error_receipt(
                    normalize_alertmanager_payload(payload),
                    code="runtime_validation_error",
                    message=str(exc),
                ),
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content=build_webhook_error_receipt(
                    normalize_alertmanager_payload(payload),
                    code="runtime_execution_failed",
                    message=str(exc),
                ),
            )

    from app.feedback.outcome_api import build_outcome_router, register_outcome_exception_handlers
    from app.receiver.signoz_ingress import build_signoz_ingress_router
    from app.receiver.signoz_queue import enqueue_admitted_warning
    from app.storage.artifact_store import JSONLArtifactStore
    from app.storage.signoz_warning_store import SignozWarningStore

    outcome_artifact_store = JSONLArtifactStore(root=Path(data_root)) if data_root else JSONLArtifactStore()
    outcome_metadata_store = MetadataStore(db_path=outcome_artifact_store.root / "metadata.sqlite3")
    outcome_retrieval_index = RetrievalIndex(db_path=outcome_artifact_store.root / "retrieval" / "retrieval.sqlite3")
    signoz_warning_store = SignozWarningStore(root=outcome_artifact_store.root)
    register_outcome_exception_handlers(app)
    app.include_router(
        build_outcome_router(
            artifact_store=outcome_artifact_store,
            metadata_store=outcome_metadata_store,
            retrieval_index=outcome_retrieval_index,
        )
    )
    app.include_router(
        build_signoz_ingress_router(
            warning_store=signoz_warning_store,
            post_accept_handler=lambda persisted: enqueue_admitted_warning(
                str(persisted["warning_id"]),
                store=signoz_warning_store,
            ),
            env=dict(os.environ),
        )
    )

    return app


def build_webhook_receipt(
    payload: AlertmanagerWebhookPayload,
    *,
    repo_root: str | Path = Path("."),
    data_root: str | Path | None = None,
    evidence_source: Literal["fixture", "live"] = "fixture",
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> WebhookReceipt:
    normalized = normalize_alertmanager_payload(payload)
    repo_root = Path(repo_root)

    from app.runtime_entry import build_runtime_execution_summary, execute_runtime_inputs
    from app.storage.artifact_store import JSONLArtifactStore

    evidence_fixture = None
    if evidence_source == "fixture":
        evidence_fixture = _resolve_evidence_fixture(normalized, repo_root=repo_root)
        evidence_bundle = _load_json(evidence_fixture)
    else:
        evidence_bundle = build_live_evidence_bundle(
            normalized,
            repo_root=repo_root,
            prometheus_collector=prometheus_collector,
            signoz_collector=signoz_collector,
            now=evidence_now,
        )
    artifact_store = JSONLArtifactStore(root=Path(data_root)) if data_root else JSONLArtifactStore()
    runtime_execution = execute_runtime_inputs(
        normalized_alert=normalized,
        evidence_bundle=evidence_bundle,
        repo_root=repo_root,
        evidence_fixture=evidence_fixture,
        artifact_store=artifact_store,
    )
    runtime_summary = build_runtime_execution_summary(runtime_execution)
    return {
        "schema_version": WEBHOOK_RECEIPT_SCHEMA_VERSION,
        "accepted": True,
        "receipt_state": "accepted",
        "normalized": normalized,
        "runtime": asdict(runtime_summary),
    }
