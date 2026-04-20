"""Durable queue and dedupe contract for admitted Signoz warnings."""

from __future__ import annotations

from typing import Any

from app.storage.signoz_warning_store import SignozWarningStore, _utc_now



def build_signoz_warning_queue_governance() -> dict[str, object]:
    return {
        "queue_mode": "strict_serial_warning_plane",
        "dedupe_scope": "active_warning_eval_window",
        "state_actions": {
            "pending": "await_worker_claim",
            "processing": "execute_canonical_runtime_spine",
            "waiting_local_primary_recovery": "retry_after_local_recovery_window",
            "failed": "bounded_retry",
            "dead_letter": "operator_intervention_required",
            "deduped": "suppress_duplicate_processing",
            "completed": "retain_runtime_artifacts_for_delivery_and_feedback",
        },
    }



def build_signoz_warning_dedupe_key(normalized_alert: dict[str, Any]) -> str:
    source_refs = normalized_alert.get("source_refs") or {}
    parts = [
        _string_or_unknown(source_refs.get("rule_id")),
        _string_or_unknown(normalized_alert.get("service")),
        _string_or_unknown(normalized_alert.get("operation")),
        _string_or_unknown(normalized_alert.get("status")),
        _string_or_unknown(source_refs.get("starts_at")),
        _string_or_unknown(source_refs.get("eval_window")),
    ]
    return "signoz-warning:" + ":".join(parts)



def enqueue_admitted_warning(
    warning_id: str,
    *,
    store: SignozWarningStore,
    now: str | None = None,
) -> dict[str, Any]:
    row = store.get_warning_row(warning_id)
    if row is None:
        raise KeyError(f"unknown warning_id: {warning_id}")
    if row.get("receipt_state") != "accepted":
        raise ValueError("only accepted Signoz warnings may enter the queue ledger")

    artifacts = store.load_warning_artifacts(warning_id)
    normalized_alert = artifacts["normalized_alert"]
    dedupe_key = build_signoz_warning_dedupe_key(normalized_alert)
    updated_at = _utc_now(now)

    existing_queue_entry = artifacts.get("queue_entry")
    if isinstance(existing_queue_entry, dict):
        return existing_queue_entry

    duplicate = store.find_duplicate(dedupe_key)
    if duplicate is not None and duplicate["warning_id"] != warning_id:
        return store.record_queue_state(
            warning_id,
            dedupe_key=dedupe_key,
            queue_state="deduped",
            updated_at=updated_at,
            duplicate_of_warning_id=str(duplicate["warning_id"]),
            attempt_count=0,
        )

    return store.record_queue_state(
        warning_id,
        dedupe_key=dedupe_key,
        queue_state="pending",
        updated_at=updated_at,
        attempt_count=0,
    )



def _string_or_unknown(value: object) -> str:
    return value if isinstance(value, str) and value else "unknown"


__all__ = [
    "build_signoz_warning_dedupe_key",
    "build_signoz_warning_queue_governance",
    "enqueue_admitted_warning",
]
