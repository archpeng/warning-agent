from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.receiver.signoz_ingress import SIGNOZ_CALLER_HEADER, SIGNOZ_INGRESS_PATH, SIGNOZ_SHARED_TOKEN_ENV
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNOZ_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "signoz-alert.prod-hq-bff-service.error.json"



def _load_signoz_payload() -> dict[str, object]:
    return json.loads(SIGNOZ_FIXTURE.read_text(encoding="utf-8"))



def _headers(*, token: str, caller_id: str = "signoz-prod") -> dict[str, str]:
    return {
        SIGNOZ_CALLER_HEADER: caller_id,
        "Authorization": f"Bearer {token}",
    }



def test_signoz_ingress_accepts_governed_warning_without_sync_runtime_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path, evidence_source="live"))

    response = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers(token="secret-token"))

    assert response.status_code == 202
    receipt = response.json()
    assert receipt["schema_version"] == "signoz-warning-ingress-receipt.v1"
    assert receipt["accepted"] is True
    assert receipt["receipt_state"] == "accepted"
    assert receipt["warning_id"].startswith("sgw_prod_hq_bff_service_post_api_datamesh_v1_charts_data")
    assert receipt["normalized"]["candidate_source"] == "signoz_alert"
    assert receipt["caller"] == {
        "caller_id": "signoz-prod",
        "auth_mode": "shared_token",
    }
    assert receipt["provenance"]["remote_source"] == "signoz_webhook"
    assert receipt["provenance"]["rule_id"] == "019d1fad-feb8-74c3-9610-dd894c6390d0"
    assert receipt["raw_payload_path"].endswith("raw_payload.json")
    assert receipt["normalized_alert_path"].endswith("normalized_alert.json")
    assert receipt["receipt_path"].endswith("admission_receipt.json")
    assert receipt["index_db_path"].endswith("signoz_warnings/index.sqlite3")
    assert "runtime" not in receipt
    assert JSONLArtifactStore(root=tmp_path).read_all("packets") == []



def test_signoz_ingress_rejects_invalid_shared_token(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers(token="wrong-token"))

    assert response.status_code == 401
    receipt = response.json()
    assert receipt["accepted"] is False
    assert receipt["receipt_state"] == "rejected"
    assert receipt["error"] == {
        "code": "auth_failed",
        "message": "shared token authentication failed",
    }



def test_signoz_ingress_rejects_malformed_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    payload = _load_signoz_payload()
    del payload["serviceName"]

    response = client.post(SIGNOZ_INGRESS_PATH, json=payload, headers=_headers(token="secret-token"))

    assert response.status_code == 422
    receipt = response.json()
    assert receipt["accepted"] is False
    assert receipt["receipt_state"] == "rejected"
    assert receipt["error"] == {
        "code": "payload_validation_error",
        "message": "missing required fields: serviceName",
    }



def test_signoz_ingress_defers_when_auth_is_not_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(SIGNOZ_SHARED_TOKEN_ENV, raising=False)
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers(token="unused-token"))

    assert response.status_code == 503
    receipt = response.json()
    assert receipt["accepted"] is False
    assert receipt["receipt_state"] == "deferred"
    assert receipt["error"] == {
        "code": "ingress_auth_unconfigured",
        "message": f"missing required ingress auth env: {SIGNOZ_SHARED_TOKEN_ENV}",
    }
