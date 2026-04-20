"""Durable Signoz warning ingress, queue, and worker state storage."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final, Literal

from app.contracts_common import DATA_DIR

QueueState = Literal[
    "pending",
    "processing",
    "waiting_local_primary_recovery",
    "completed",
    "failed",
    "dead_letter",
    "deduped",
]

_SIGNOZ_WARNING_DIR: Final = "signoz_warnings"
_WARNING_INDEX_DB: Final = "index.sqlite3"
_WARNING_QUEUE_SCHEMA_VERSION: Final = "signoz-warning-queue-entry.v1"
_WARNING_PROCESSING_SCHEMA_VERSION: Final = "signoz-warning-processing-result.v1"
_ACTIVE_DEDUPE_STATES: Final[tuple[QueueState, ...]] = (
    "pending",
    "processing",
    "waiting_local_primary_recovery",
    "completed",
    "failed",
)


@dataclass(frozen=True)
class PersistedSignozWarningPaths:
    warning_dir: Path
    raw_payload_path: Path
    normalized_alert_path: Path
    receipt_path: Path
    queue_entry_path: Path
    processing_result_path: Path
    index_db_path: Path


@dataclass(frozen=True)
class ClaimedWarning:
    warning_id: str
    row: dict[str, object]



def _utc_now(now: str | None = None) -> str:
    if now is not None:
        return now
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")



def _parse_utc(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)



def _slug(value: str | None) -> str:
    if not value:
        return "unknown"
    chars: list[str] = []
    last_was_sep = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            last_was_sep = False
            continue
        if not last_was_sep:
            chars.append("_")
            last_was_sep = True
    return "".join(chars).strip("_") or "unknown"



def _compact_timestamp(timestamp: str) -> str:
    return _parse_utc(timestamp).strftime("%Y%m%dt%H%M%Sz").lower()



def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class SignozWarningStore:
    def __init__(self, root: str | Path = DATA_DIR) -> None:
        self.root = Path(root)
        self.warning_root = self.root / _SIGNOZ_WARNING_DIR
        self.db_path = self.warning_root / _WARNING_INDEX_DB
        self.warning_root.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signoz_warnings (
                    warning_id TEXT PRIMARY KEY,
                    service TEXT,
                    operation TEXT,
                    rule_id TEXT,
                    warning_status TEXT,
                    receipt_state TEXT,
                    caller_id TEXT,
                    auth_mode TEXT,
                    received_at TEXT NOT NULL,
                    raw_payload_path TEXT NOT NULL,
                    normalized_alert_path TEXT NOT NULL,
                    receipt_path TEXT NOT NULL,
                    queue_entry_path TEXT,
                    processing_result_path TEXT,
                    dedupe_key TEXT,
                    queue_state TEXT,
                    duplicate_of_warning_id TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    next_attempt_after TEXT,
                    leased_by TEXT,
                    leased_at TEXT,
                    runtime_packet_id TEXT,
                    runtime_decision_id TEXT,
                    runtime_report_id TEXT,
                    investigation_stage TEXT,
                    delivery_status TEXT,
                    evidence_state TEXT,
                    human_review_required INTEGER NOT NULL DEFAULT 0,
                    last_error_code TEXT,
                    last_error_message TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_signoz_warnings_queue_state ON signoz_warnings(queue_state, received_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_signoz_warnings_dedupe_key ON signoz_warnings(dedupe_key)"
            )
            connection.commit()

    def build_warning_id(
        self,
        *,
        received_at: str,
        service: str | None,
        operation: str | None,
        rule_id: str | None,
    ) -> str:
        return "sgw_" + "_".join(
            [
                _slug(service),
                _slug(operation),
                _slug(rule_id),
                _compact_timestamp(received_at),
            ]
        )

    def warning_dir(self, warning_id: str) -> Path:
        return self.warning_root / warning_id

    def _ensure_unique_warning_id(self, warning_id: str) -> str:
        if self.get_warning_row(warning_id) is None and not self.warning_dir(warning_id).exists():
            return warning_id
        suffix = 2
        while True:
            candidate = f"{warning_id}_{suffix}"
            if self.get_warning_row(candidate) is None and not self.warning_dir(candidate).exists():
                return candidate
            suffix += 1

    def build_paths(self, warning_id: str) -> PersistedSignozWarningPaths:
        warning_dir = self.warning_dir(warning_id)
        return PersistedSignozWarningPaths(
            warning_dir=warning_dir,
            raw_payload_path=warning_dir / "raw_payload.json",
            normalized_alert_path=warning_dir / "normalized_alert.json",
            receipt_path=warning_dir / "admission_receipt.json",
            queue_entry_path=warning_dir / "queue_entry.json",
            processing_result_path=warning_dir / "processing_result.json",
            index_db_path=self.db_path,
        )

    def persist_admission(
        self,
        *,
        raw_payload: dict[str, Any],
        normalized_alert: dict[str, Any],
        receipt: dict[str, Any],
        warning_id: str | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        received_at = str(receipt["provenance"]["received_at"])
        source_refs = normalized_alert.get("source_refs") or {}
        warning_id = warning_id or self.build_warning_id(
            received_at=received_at,
            service=_string_or_none(normalized_alert.get("service")),
            operation=_string_or_none(normalized_alert.get("operation")),
            rule_id=_string_or_none(source_refs.get("rule_id")),
        )
        warning_id = self._ensure_unique_warning_id(warning_id)
        paths = self.build_paths(warning_id)

        raw_payload_path = _write_json(paths.raw_payload_path, raw_payload)
        normalized_alert_path = _write_json(paths.normalized_alert_path, normalized_alert)
        receipt_payload = {
            **receipt,
            "warning_id": warning_id,
            "raw_payload_path": str(raw_payload_path),
            "normalized_alert_path": str(normalized_alert_path),
            "receipt_path": str(paths.receipt_path),
            "index_db_path": str(self.db_path),
        }
        receipt_path = _write_json(paths.receipt_path, receipt_payload)

        caller = receipt.get("caller") or {}
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO signoz_warnings (
                    warning_id,
                    service,
                    operation,
                    rule_id,
                    warning_status,
                    receipt_state,
                    caller_id,
                    auth_mode,
                    received_at,
                    raw_payload_path,
                    normalized_alert_path,
                    receipt_path,
                    queue_entry_path,
                    processing_result_path,
                    dedupe_key,
                    queue_state,
                    duplicate_of_warning_id,
                    attempt_count,
                    next_attempt_after,
                    leased_by,
                    leased_at,
                    runtime_packet_id,
                    runtime_decision_id,
                    runtime_report_id,
                    investigation_stage,
                    delivery_status,
                    evidence_state,
                    human_review_required,
                    last_error_code,
                    last_error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    warning_id,
                    _string_or_none(normalized_alert.get("service")),
                    _string_or_none(normalized_alert.get("operation")),
                    _string_or_none(source_refs.get("rule_id")),
                    _string_or_none(normalized_alert.get("status")),
                    _string_or_none(receipt_payload.get("receipt_state")),
                    _string_or_none(caller.get("caller_id")),
                    _string_or_none(caller.get("auth_mode")),
                    received_at,
                    str(raw_payload_path),
                    str(normalized_alert_path),
                    str(receipt_path),
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                ),
            )
            connection.commit()

        return {
            **receipt_payload,
            "warning_id": warning_id,
            "raw_payload_path": str(raw_payload_path),
            "normalized_alert_path": str(normalized_alert_path),
            "receipt_path": str(receipt_path),
            "index_db_path": str(self.db_path),
        }

    def get_warning_row(self, warning_id: str) -> dict[str, Any] | None:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM signoz_warnings WHERE warning_id = ?",
                (warning_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_warning_rows(self) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM signoz_warnings ORDER BY received_at, warning_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def load_warning_artifacts(self, warning_id: str) -> dict[str, Any]:
        row = self.get_warning_row(warning_id)
        if row is None:
            raise KeyError(f"unknown warning_id: {warning_id}")
        return {
            "row": row,
            "raw_payload": json.loads(Path(str(row["raw_payload_path"])).read_text(encoding="utf-8")),
            "normalized_alert": json.loads(Path(str(row["normalized_alert_path"])).read_text(encoding="utf-8")),
            "receipt": json.loads(Path(str(row["receipt_path"])).read_text(encoding="utf-8")),
            "queue_entry": (
                json.loads(Path(str(row["queue_entry_path"])).read_text(encoding="utf-8"))
                if row.get("queue_entry_path")
                else None
            ),
            "processing_result": (
                json.loads(Path(str(row["processing_result_path"])).read_text(encoding="utf-8"))
                if row.get("processing_result_path")
                else None
            ),
        }

    def find_duplicate(self, dedupe_key: str) -> dict[str, Any] | None:
        self.initialize()
        placeholders = ",".join("?" for _ in _ACTIVE_DEDUPE_STATES)
        with self.connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM signoz_warnings
                WHERE dedupe_key = ? AND queue_state IN ({placeholders})
                ORDER BY received_at, warning_id
                LIMIT 1
                """,
                (dedupe_key, *_ACTIVE_DEDUPE_STATES),
            ).fetchone()
        return dict(row) if row is not None else None

    def record_queue_state(
        self,
        warning_id: str,
        *,
        dedupe_key: str,
        queue_state: QueueState,
        updated_at: str,
        duplicate_of_warning_id: str | None = None,
        attempt_count: int = 0,
        next_attempt_after: str | None = None,
        leased_by: str | None = None,
        leased_at: str | None = None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
        deferred_reason_code: str | None = None,
        deferred_reason_message: str | None = None,
        policy_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        row = self.get_warning_row(warning_id)
        if row is None:
            raise KeyError(f"unknown warning_id: {warning_id}")
        payload = {
            "schema_version": _WARNING_QUEUE_SCHEMA_VERSION,
            "warning_id": warning_id,
            "dedupe_key": dedupe_key,
            "queue_state": queue_state,
            "duplicate_of_warning_id": duplicate_of_warning_id,
            "attempt_count": attempt_count,
            "next_attempt_after": next_attempt_after,
            "leased_by": leased_by,
            "leased_at": leased_at,
            "updated_at": updated_at,
            "last_error": (
                {
                    "code": last_error_code,
                    "message": last_error_message,
                }
                if last_error_code or last_error_message
                else None
            ),
            "deferred_reason": (
                {
                    "code": deferred_reason_code,
                    "message": deferred_reason_message,
                }
                if deferred_reason_code or deferred_reason_message
                else None
            ),
            "policy_state": policy_state,
        }
        queue_entry_path = _write_json(self.build_paths(warning_id).queue_entry_path, payload)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE signoz_warnings
                SET dedupe_key = ?,
                    queue_state = ?,
                    duplicate_of_warning_id = ?,
                    attempt_count = ?,
                    next_attempt_after = ?,
                    leased_by = ?,
                    leased_at = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    queue_entry_path = ?
                WHERE warning_id = ?
                """,
                (
                    dedupe_key,
                    queue_state,
                    duplicate_of_warning_id,
                    attempt_count,
                    next_attempt_after,
                    leased_by,
                    leased_at,
                    last_error_code,
                    last_error_message,
                    str(queue_entry_path),
                    warning_id,
                ),
            )
            connection.commit()
        return payload

    def claim_next_warning(
        self,
        *,
        lease_owner: str,
        now: str,
    ) -> ClaimedWarning | None:
        self.initialize()
        now_dt = _parse_utc(now)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM signoz_warnings
                WHERE queue_state IN ('pending', 'failed', 'waiting_local_primary_recovery')
                ORDER BY received_at, warning_id
                """
            ).fetchall()
            for raw_row in rows:
                row = dict(raw_row)
                if row["queue_state"] in {"failed", "waiting_local_primary_recovery"} and row.get("next_attempt_after"):
                    if _parse_utc(str(row["next_attempt_after"])) > now_dt:
                        continue
                dedupe_key = str(row["dedupe_key"] or "")
                attempt_count = int(row["attempt_count"] or 0) + 1
                leased_at = now
                connection.execute(
                    """
                    UPDATE signoz_warnings
                    SET queue_state = 'processing',
                        attempt_count = ?,
                        leased_by = ?,
                        leased_at = ?,
                        next_attempt_after = NULL,
                        last_error_code = NULL,
                        last_error_message = NULL
                    WHERE warning_id = ?
                    """,
                    (attempt_count, lease_owner, leased_at, row["warning_id"]),
                )
                connection.commit()
                self.record_queue_state(
                    str(row["warning_id"]),
                    dedupe_key=dedupe_key,
                    queue_state="processing",
                    updated_at=now,
                    duplicate_of_warning_id=_string_or_none(row.get("duplicate_of_warning_id")),
                    attempt_count=attempt_count,
                    leased_by=lease_owner,
                    leased_at=leased_at,
                )
                claimed = self.get_warning_row(str(row["warning_id"]))
                assert claimed is not None
                return ClaimedWarning(warning_id=str(row["warning_id"]), row=claimed)
        return None

    def mark_warning_waiting_for_local_primary_recovery(
        self,
        warning_id: str,
        *,
        now: str,
        retry_backoff_sec: int,
        resident_lifecycle: dict[str, Any],
        abnormal_path: dict[str, Any],
    ) -> dict[str, Any]:
        row = self.get_warning_row(warning_id)
        if row is None:
            raise KeyError(f"unknown warning_id: {warning_id}")
        next_attempt_after = (
            _parse_utc(now) + timedelta(seconds=retry_backoff_sec)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return self.record_queue_state(
            warning_id,
            dedupe_key=str(row["dedupe_key"] or ""),
            queue_state="waiting_local_primary_recovery",
            updated_at=now,
            duplicate_of_warning_id=_string_or_none(row.get("duplicate_of_warning_id")),
            attempt_count=int(row["attempt_count"] or 0),
            next_attempt_after=next_attempt_after,
            leased_by=None,
            leased_at=None,
            deferred_reason_code="local_primary_recovery_wait",
            deferred_reason_message=str(abnormal_path.get("reason") or "waiting for local primary recovery"),
            policy_state={
                "resident_lifecycle": resident_lifecycle,
                "abnormal_path": abnormal_path,
            },
        )

    def mark_warning_failed(
        self,
        warning_id: str,
        *,
        max_attempts: int,
        retry_backoff_sec: int,
        now: str,
        error_code: str,
        error_message: str,
    ) -> dict[str, Any]:
        row = self.get_warning_row(warning_id)
        if row is None:
            raise KeyError(f"unknown warning_id: {warning_id}")
        attempt_count = int(row["attempt_count"] or 0)
        if attempt_count >= max_attempts:
            queue_state: QueueState = "dead_letter"
            next_attempt_after = None
        else:
            queue_state = "failed"
            next_attempt_after = (
                _parse_utc(now) + timedelta(seconds=retry_backoff_sec)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return self.record_queue_state(
            warning_id,
            dedupe_key=str(row["dedupe_key"] or ""),
            queue_state=queue_state,
            updated_at=now,
            duplicate_of_warning_id=_string_or_none(row.get("duplicate_of_warning_id")),
            attempt_count=attempt_count,
            next_attempt_after=next_attempt_after,
            leased_by=None,
            leased_at=None,
            last_error_code=error_code,
            last_error_message=error_message,
        )

    def record_processing_result(
        self,
        warning_id: str,
        *,
        updated_at: str,
        packet_id: str,
        decision_id: str,
        report_id: str,
        investigation_stage: str,
        delivery_status: str | None,
        evidence_state: str,
        human_review_required: bool,
        recommended_action: str | None,
        runtime_artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        row = self.get_warning_row(warning_id)
        if row is None:
            raise KeyError(f"unknown warning_id: {warning_id}")
        payload = {
            "schema_version": _WARNING_PROCESSING_SCHEMA_VERSION,
            "warning_id": warning_id,
            "queue_state": "completed",
            "updated_at": updated_at,
            "packet_id": packet_id,
            "decision_id": decision_id,
            "report_id": report_id,
            "investigation_stage": investigation_stage,
            "delivery_status": delivery_status,
            "evidence_state": evidence_state,
            "human_review_required": human_review_required,
            "recommended_action": recommended_action,
            "runtime_artifacts": runtime_artifacts,
        }
        processing_result_path = _write_json(self.build_paths(warning_id).processing_result_path, payload)
        self.record_queue_state(
            warning_id,
            dedupe_key=str(row["dedupe_key"] or ""),
            queue_state="completed",
            updated_at=updated_at,
            duplicate_of_warning_id=_string_or_none(row.get("duplicate_of_warning_id")),
            attempt_count=int(row["attempt_count"] or 0),
        )
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE signoz_warnings
                SET processing_result_path = ?,
                    runtime_packet_id = ?,
                    runtime_decision_id = ?,
                    runtime_report_id = ?,
                    investigation_stage = ?,
                    delivery_status = ?,
                    evidence_state = ?,
                    human_review_required = ?,
                    leased_by = NULL,
                    leased_at = NULL,
                    last_error_code = NULL,
                    last_error_message = NULL
                WHERE warning_id = ?
                """,
                (
                    str(processing_result_path),
                    packet_id,
                    decision_id,
                    report_id,
                    investigation_stage,
                    delivery_status,
                    evidence_state,
                    1 if human_review_required else 0,
                    warning_id,
                ),
            )
            connection.commit()
        return payload

    def queue_metrics(self, *, now: str | None = None) -> dict[str, Any]:
        rows = self.list_warning_rows()
        now_value = _utc_now(now)
        counts = {
            "pending": 0,
            "processing": 0,
            "waiting_local_primary_recovery": 0,
            "completed": 0,
            "failed": 0,
            "dead_letter": 0,
            "deduped": 0,
        }
        oldest_pending_age_sec: int | None = None
        oldest_local_primary_recovery_wait_age_sec: int | None = None
        delivery_deferred_count = 0
        cloud_fallback_completed = 0
        completed_with_runtime = 0
        for row in rows:
            queue_state = _string_or_none(row.get("queue_state"))
            if queue_state in counts:
                counts[queue_state] += 1
            if queue_state == "pending":
                age_sec = int((_parse_utc(now_value) - _parse_utc(str(row["received_at"]))).total_seconds())
                oldest_pending_age_sec = age_sec if oldest_pending_age_sec is None else min(oldest_pending_age_sec, age_sec)
            if queue_state == "waiting_local_primary_recovery":
                wait_age_sec = int((_parse_utc(now_value) - _parse_utc(str(row["received_at"]))).total_seconds())
                oldest_local_primary_recovery_wait_age_sec = (
                    wait_age_sec
                    if oldest_local_primary_recovery_wait_age_sec is None
                    else min(oldest_local_primary_recovery_wait_age_sec, wait_age_sec)
                )
            if row.get("delivery_status") == "deferred":
                delivery_deferred_count += 1
            if row.get("runtime_report_id"):
                completed_with_runtime += 1
                if row.get("investigation_stage") == "cloud_fallback":
                    cloud_fallback_completed += 1
        backlog_size = (
            counts["pending"]
            + counts["processing"]
            + counts["waiting_local_primary_recovery"]
            + counts["failed"]
        )
        return {
            "queue_states": counts,
            "backlog_size": backlog_size,
            "oldest_pending_age_sec": oldest_pending_age_sec,
            "oldest_local_primary_recovery_wait_age_sec": oldest_local_primary_recovery_wait_age_sec,
            "processing_failure_count": counts["failed"] + counts["dead_letter"],
            "local_primary_recovery_wait_count": counts["waiting_local_primary_recovery"],
            "delivery_deferred_count": delivery_deferred_count,
            "cloud_fallback_ratio": (
                round(cloud_fallback_completed / completed_with_runtime, 4) if completed_with_runtime else 0.0
            ),
        }



def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "ClaimedWarning",
    "PersistedSignozWarningPaths",
    "QueueState",
    "SignozWarningStore",
    "_utc_now",
]
