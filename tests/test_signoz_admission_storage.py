from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.receiver.signoz_ingress import SIGNOZ_CALLER_HEADER, SIGNOZ_INGRESS_PATH, SIGNOZ_SHARED_TOKEN_ENV
from app.storage.signoz_warning_store import SignozWarningStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNOZ_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "signoz-alert.prod-hq-bff-service.error.json"



def _load_signoz_payload() -> dict[str, object]:
    return json.loads(SIGNOZ_FIXTURE.read_text(encoding="utf-8"))



def test_signoz_ingress_persists_raw_normalized_receipt_and_provenance_layers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(
        SIGNOZ_INGRESS_PATH,
        json=_load_signoz_payload(),
        headers={
            SIGNOZ_CALLER_HEADER: "signoz-prod",
            "Authorization": "Bearer secret-token",
        },
    )

    assert response.status_code == 202
    receipt = response.json()
    warning_id = receipt["warning_id"]
    assert warning_id is not None

    store = SignozWarningStore(root=tmp_path)
    row = store.get_warning_row(warning_id)
    assert row is not None
    assert row["service"] == "prod-hq-bff-service"
    assert row["operation"] == "POST /api/datamesh/v1/charts/data"
    assert row["rule_id"] == "019d1fad-feb8-74c3-9610-dd894c6390d0"
    assert row["receipt_state"] == "accepted"
    assert row["caller_id"] == "signoz-prod"
    assert row["auth_mode"] == "shared_token"
    assert Path(str(row["raw_payload_path"])).exists()
    assert Path(str(row["normalized_alert_path"])).exists()
    assert Path(str(row["receipt_path"])).exists()

    artifacts = store.load_warning_artifacts(warning_id)
    assert artifacts["raw_payload"] == _load_signoz_payload()
    assert artifacts["normalized_alert"]["candidate_source"] == "signoz_alert"
    assert artifacts["receipt"]["warning_id"] == warning_id
    assert artifacts["receipt"]["caller"] == {
        "caller_id": "signoz-prod",
        "auth_mode": "shared_token",
    }
    assert artifacts["receipt"]["provenance"]["remote_source"] == "signoz_webhook"
    assert artifacts["receipt"]["raw_payload_path"] == str(Path(str(row["raw_payload_path"])))
    assert artifacts["receipt"]["normalized_alert_path"] == str(Path(str(row["normalized_alert_path"])))
    assert artifacts["receipt"]["receipt_path"] == str(Path(str(row["receipt_path"])))
    assert artifacts["receipt"]["index_db_path"] == str(store.db_path)
