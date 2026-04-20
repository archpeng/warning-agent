"""Bounded worker runtime for durable Signoz warnings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.collectors.evidence_bundle import build_signoz_first_evidence_bundle
from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector
from app.investigator.local_primary import (
    local_primary_abnormal_path_payload,
    local_primary_resident_lifecycle_payload,
)
from app.investigator.runtime import LocalPrimaryRecoveryRequired
from app.runtime_entry import build_runtime_execution_summary, execute_runtime_inputs
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.signoz_warning_store import SignozWarningStore, _utc_now

WorkerProcessor = Callable[[str], dict[str, Any]]



def classify_signoz_evidence_state(evidence_bundle: dict[str, Any]) -> str:
    signoz = evidence_bundle.get("signoz") or {}
    trace_ids = signoz.get("sample_trace_ids") or []
    log_refs = signoz.get("sample_log_refs") or []
    trace_error_ratio = signoz.get("trace_error_ratio")
    return "complete" if trace_error_ratio is not None and (trace_ids or log_refs) else "partial"



def build_completed_processing_result(
    *,
    execution,
    evidence_bundle: dict[str, Any],
    artifact_store: JSONLArtifactStore,
) -> dict[str, Any]:
    summary = build_runtime_execution_summary(execution)
    persisted = execution.persisted_artifacts
    assert persisted is not None
    delivery_records = [
        record
        for record in artifact_store.read_all("deliveries")
        if str(record.get("report_id")) == summary.report_id
    ]
    latest_delivery = delivery_records[-1] if delivery_records else None
    recommended_action = execution.decision.get("recommended_action")
    recommended_action = recommended_action if isinstance(recommended_action, str) else None
    delivery_status = str(latest_delivery.get("status")) if latest_delivery is not None else None
    human_review_required = recommended_action == "send_to_human_review" or delivery_status == "deferred"
    return {
        "packet_id": summary.packet_id,
        "decision_id": summary.decision_id,
        "report_id": summary.report_id,
        "investigation_stage": summary.investigation_stage,
        "delivery_status": delivery_status,
        "evidence_state": classify_signoz_evidence_state(evidence_bundle),
        "human_review_required": human_review_required,
        "recommended_action": recommended_action,
        "runtime_artifacts": {
            "packet_path": str(persisted.packet_path),
            "decision_path": str(persisted.decision_path),
            "investigation_path": str(persisted.investigation_path) if persisted.investigation_path else None,
            "report_path": str(persisted.report_path),
            "delivery_dispatches_path": (
                str(persisted.delivery_dispatches_path) if persisted.delivery_dispatches_path else None
            ),
            "metadata_db_path": str(persisted.metadata_db_path) if persisted.metadata_db_path else None,
            "retrieval_db_path": str(persisted.retrieval_db_path) if persisted.retrieval_db_path else None,
            "rollout_evidence_path": str(persisted.rollout_evidence_path) if persisted.rollout_evidence_path else None,
        },
    }



def execute_admitted_signoz_warning(
    warning_id: str,
    *,
    store: SignozWarningStore,
    repo_root: str | Path = Path("."),
    artifact_store: JSONLArtifactStore | None = None,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    loaded = store.load_warning_artifacts(warning_id)
    normalized_alert = loaded["normalized_alert"]
    artifact_store = artifact_store or JSONLArtifactStore(root=store.root)

    evidence_bundle = build_signoz_first_evidence_bundle(
        normalized_alert,
        repo_root=repo_root,
        prometheus_collector=prometheus_collector,
        signoz_collector=signoz_collector,
        now=evidence_now,
    )
    execution = execute_runtime_inputs(
        normalized_alert=normalized_alert,
        evidence_bundle=evidence_bundle,
        repo_root=repo_root,
        artifact_store=artifact_store,
        runtime_context="warning_worker",
    )
    return build_completed_processing_result(
        execution=execution,
        evidence_bundle=evidence_bundle,
        artifact_store=artifact_store,
    )



def run_signoz_worker_once(
    *,
    store: SignozWarningStore,
    repo_root: str | Path = Path("."),
    lease_owner: str = "warning-agent-signoz-worker",
    now: str | None = None,
    max_attempts: int = 3,
    retry_backoff_sec: int = 30,
    processor: WorkerProcessor | None = None,
    artifact_store: JSONLArtifactStore | None = None,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> dict[str, Any] | None:
    now_value = _utc_now(now)
    claimed = store.claim_next_warning(lease_owner=lease_owner, now=now_value)
    if claimed is None:
        return None

    processor = processor or (
        lambda warning_id: execute_admitted_signoz_warning(
            warning_id,
            store=store,
            repo_root=repo_root,
            artifact_store=artifact_store,
            prometheus_collector=prometheus_collector,
            signoz_collector=signoz_collector,
            evidence_now=evidence_now,
        )
    )

    try:
        result = processor(claimed.warning_id)
    except LocalPrimaryRecoveryRequired as exc:
        queue_entry = store.mark_warning_waiting_for_local_primary_recovery(
            claimed.warning_id,
            now=now_value,
            retry_backoff_sec=retry_backoff_sec,
            resident_lifecycle=local_primary_resident_lifecycle_payload(exc.signal.resident_lifecycle),
            abnormal_path=local_primary_abnormal_path_payload(exc.signal.abnormal_path),
        )
        return {
            "warning_id": claimed.warning_id,
            "queue": queue_entry,
            "recovery_wait": {
                "resident_lifecycle": local_primary_resident_lifecycle_payload(exc.signal.resident_lifecycle),
                "abnormal_path": local_primary_abnormal_path_payload(exc.signal.abnormal_path),
            },
        }
    except Exception as exc:
        queue_entry = store.mark_warning_failed(
            claimed.warning_id,
            max_attempts=max_attempts,
            retry_backoff_sec=retry_backoff_sec,
            now=now_value,
            error_code="worker_execution_failed",
            error_message=str(exc),
        )
        return {
            "warning_id": claimed.warning_id,
            "queue": queue_entry,
        }

    processing_result = store.record_processing_result(
        claimed.warning_id,
        updated_at=now_value,
        packet_id=str(result["packet_id"]),
        decision_id=str(result["decision_id"]),
        report_id=str(result["report_id"]),
        investigation_stage=str(result["investigation_stage"]),
        delivery_status=(str(result["delivery_status"]) if result.get("delivery_status") is not None else None),
        evidence_state=str(result["evidence_state"]),
        human_review_required=bool(result["human_review_required"]),
        recommended_action=(str(result["recommended_action"]) if result.get("recommended_action") else None),
        runtime_artifacts=dict(result["runtime_artifacts"]),
    )
    return {
        "warning_id": claimed.warning_id,
        "queue": store.load_warning_artifacts(claimed.warning_id)["queue_entry"],
        "processing_result": processing_result,
    }


__all__ = [
    "build_completed_processing_result",
    "classify_signoz_evidence_state",
    "execute_admitted_signoz_warning",
    "run_signoz_worker_once",
]
