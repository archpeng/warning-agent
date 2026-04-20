from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.receiver.signoz_ingress import SIGNOZ_CALLER_HEADER, SIGNOZ_INGRESS_PATH, SIGNOZ_SHARED_TOKEN_ENV
from app.receiver.signoz_queue import build_signoz_warning_dedupe_key
from app.storage.signoz_warning_store import SignozWarningStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNOZ_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "signoz-alert.prod-hq-bff-service.error.json"



def _load_signoz_payload() -> dict[str, object]:
    return json.loads(SIGNOZ_FIXTURE.read_text(encoding="utf-8"))



def _headers() -> dict[str, str]:
    return {
        SIGNOZ_CALLER_HEADER: "signoz-prod",
        "Authorization": "Bearer secret-token",
    }



def test_signoz_ingress_enqueues_first_accepted_warning_as_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())

    assert response.status_code == 202
    receipt = response.json()
    assert receipt["queue"] == {
        "schema_version": "signoz-warning-queue-entry.v1",
        "warning_id": receipt["warning_id"],
        "dedupe_key": build_signoz_warning_dedupe_key(receipt["normalized"]),
        "queue_state": "pending",
        "duplicate_of_warning_id": None,
        "attempt_count": 0,
        "next_attempt_after": None,
        "leased_by": None,
        "leased_at": None,
        "updated_at": receipt["queue"]["updated_at"],
        "last_error": None,
    }

    store = SignozWarningStore(root=tmp_path)
    row = store.get_warning_row(receipt["warning_id"])
    assert row is not None
    assert row["queue_state"] == "pending"
    assert row["dedupe_key"] == build_signoz_warning_dedupe_key(receipt["normalized"])



def test_signoz_ingress_marks_duplicate_warning_as_deduped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    first = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())
    second = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())

    assert first.status_code == 202
    assert second.status_code == 202
    first_receipt = first.json()
    second_receipt = second.json()
    assert first_receipt["queue"]["queue_state"] == "pending"
    assert second_receipt["queue"]["queue_state"] == "deduped"
    assert second_receipt["queue"]["duplicate_of_warning_id"] == first_receipt["warning_id"]

    store = SignozWarningStore(root=tmp_path)
    rows = store.list_warning_rows()
    assert [row["queue_state"] for row in rows] == ["pending", "deduped"]
    assert rows[1]["duplicate_of_warning_id"] == first_receipt["warning_id"]
