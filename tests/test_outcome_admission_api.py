from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTCOME_ADMIT_PATH = "/outcome/admit"


def _valid_admission_payload() -> dict:
    return {
        "source": "operator",
        "recorded_at": "2026-04-19T08:00:00Z",
        "service": "checkout",
        "operation": "POST /api/pay",
        "environment": "prod",
        "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
        "decision_id": "lad_checkout_post_pay_20260418t120010z",
        "investigation_id": "inv_checkout_post_pay_20260418t120012z",
        "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
        "known_outcome": "severe",
        "final_severity_band": "P1",
        "final_recommended_action": "page_owner",
        "resolution_summary": "operator confirmed a real incident and resolved it with a rollback",
        "notes": ["rollback applied"],
        "evidence_links": {"ticket_id": "TICKET-123"},
    }


def test_admit_outcome_returns_success_receipt_and_persists_all_layers(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    response = client.post(OUTCOME_ADMIT_PATH, json=_valid_admission_payload())

    assert response.status_code == 200
    receipt = response.json()
    assert receipt["schema_version"] == "outcome-admission-receipt.v1"
    assert receipt["admitted"] is True
    assert receipt["receipt_state"] == "admitted"
    assert receipt["outcome_id"] == "out_operator_checkout_post_api_pay_20260419t080000z"
    assert receipt["artifact_path"] == str(tmp_path / "outcomes" / "outcomes.jsonl")
    assert receipt["metadata_db_path"] == str(tmp_path / "metadata.sqlite3")
    assert receipt["metadata_artifact_id"] == "out_operator_checkout_post_api_pay_20260419t080000z"
    assert receipt["retrieval_refreshed"] is True
    assert receipt["retrieval_refreshed_count"] == 1
    assert receipt["retrieval_refreshed_doc_ids"] == ["out_operator_checkout_post_api_pay_20260419t080000z"]
    assert receipt["retrieval_db_path"] == str(tmp_path / "retrieval" / "retrieval.sqlite3")

    artifact_store = JSONLArtifactStore(root=tmp_path)
    outcome_records = artifact_store.read_all("outcomes")
    assert [r["outcome_id"] for r in outcome_records] == ["out_operator_checkout_post_api_pay_20260419t080000z"]

    metadata_store = MetadataStore(db_path=tmp_path / "metadata.sqlite3")
    assert metadata_store.list_artifacts("outcomes") == [
        {
            "artifact_id": "out_operator_checkout_post_api_pay_20260419t080000z",
            "schema_version": "incident-outcome.v1",
            "service": "checkout",
            "operation": "POST /api/pay",
            "created_at": "2026-04-19T08:00:00Z",
            "artifact_path": str(tmp_path / "outcomes" / "outcomes.jsonl"),
        }
    ]

    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")
    hits = search_documents(retrieval_index, "rollback severe", service="checkout")
    assert [hit.doc_id for hit in hits] == ["out_operator_checkout_post_api_pay_20260419t080000z"]
    assert hits[0].kind == "outcome"


def test_admit_outcome_returns_error_receipt_for_missing_required_field(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    payload = _valid_admission_payload()
    del payload["service"]

    response = client.post(OUTCOME_ADMIT_PATH, json=payload)

    assert response.status_code == 422
    receipt = response.json()
    assert receipt["schema_version"] == "outcome-admission-receipt.v1"
    assert receipt["admitted"] is False
    assert receipt["receipt_state"] == "rejected"
    assert receipt["outcome_id"] is None
    assert receipt["metadata_artifact_id"] is None
    assert receipt["retrieval_refreshed_count"] == 0
    assert receipt["retrieval_refreshed_doc_ids"] == []
    assert receipt["error"]["code"] == "validation_error"


def test_admit_outcome_returns_error_receipt_for_invalid_outcome_schema(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    payload = _valid_admission_payload()
    payload["known_outcome"] = "invalid_value"

    response = client.post(OUTCOME_ADMIT_PATH, json=payload)

    assert response.status_code == 422
    receipt = response.json()
    assert receipt["schema_version"] == "outcome-admission-receipt.v1"
    assert receipt["admitted"] is False
    assert receipt["receipt_state"] == "rejected"
    assert receipt["metadata_artifact_id"] is None
    assert receipt["retrieval_refreshed_count"] == 0
    assert receipt["retrieval_refreshed_doc_ids"] == []
    assert receipt["error"]["code"] == "schema_validation_error"


def test_admit_outcome_returns_error_receipt_for_malformed_timestamp(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    payload = _valid_admission_payload()
    payload["recorded_at"] = "not-a-timestamp"

    response = client.post(OUTCOME_ADMIT_PATH, json=payload)

    assert response.status_code == 422
    receipt = response.json()
    assert receipt["schema_version"] == "outcome-admission-receipt.v1"
    assert receipt["admitted"] is False
    assert receipt["receipt_state"] == "rejected"
    assert receipt["metadata_artifact_id"] is None
    assert receipt["retrieval_refreshed_count"] == 0
    assert receipt["retrieval_refreshed_doc_ids"] == []
    assert receipt["error"]["code"] == "schema_validation_error"
