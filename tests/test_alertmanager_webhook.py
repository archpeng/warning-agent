from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.delivery.bridge_result import BridgeDispatchResult
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.receiver.alertmanager_webhook import (
    WEBHOOK_PATH,
    create_app,
    normalize_alertmanager_payload,
)
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"



def _seed_checkout_outcome_retrieval(data_root: Path) -> None:
    artifact_store = JSONLArtifactStore(root=data_root)
    retrieval_index = RetrievalIndex(db_path=data_root / "retrieval" / "retrieval.sqlite3")
    ingest_incident_outcome(
        OutcomeIngestRequest(
            source="operator",
            recorded_at="2026-04-19T08:00:00Z",
            service="checkout",
            operation="POST /api/pay",
            environment="prod",
            packet_id="ipk_checkout_reference_20260417t090000z",
            decision_id="lad_checkout_reference_20260417t090002z",
            investigation_id="cir_checkout_reference_20260417t090024z_cloud",
            report_id="rpt_checkout_reference_20260417t090000z",
            known_outcome="severe",
            final_severity_band="P1",
            final_recommended_action="page_owner",
            resolution_summary="operator confirmed the checkout timeout incident and rolled back the release",
            notes=("db timeout on order lookup recurred before rollback",),
        ),
        artifact_store=artifact_store,
    )
    refresh_outcome_retrieval_docs(artifact_store=artifact_store, retrieval_index=retrieval_index)



def _load_alert_payload() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        envelope = json.load(handle)
    return envelope["alert_payload"]


def test_normalized_payload_matches_replay_fixture_shape() -> None:
    normalized = normalize_alertmanager_payload(
        _load_alert_payload(),
        candidate_source="manual_replay",
    )

    assert normalized == {
        "candidate_source": "manual_replay",
        "receiver": "warning-agent",
        "status": "firing",
        "alert_count": 1,
        "alertname": "HighErrorRate",
        "environment": "prod",
        "service": "checkout",
        "operation": "POST /api/pay",
        "group_key": '{}:{alertname="HighErrorRate",service="checkout"}',
        "common_labels": {
            "alertname": "HighErrorRate",
            "service": "checkout",
            "severity": "critical",
            "environment": "prod",
            "operation": "POST /api/pay",
        },
        "common_annotations": {
            "summary": "checkout POST /api/pay error rate is above threshold",
        },
    }


def test_webhook_stub_accepts_payload_and_returns_runtime_receipt(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    response = client.post(WEBHOOK_PATH, json=_load_alert_payload())

    assert response.status_code == 200

    payload = response.json()
    assert payload["schema_version"] == "alertmanager-webhook-receipt.v1"
    assert payload["receipt_state"] == "accepted"
    assert payload["runtime"]["packet_id"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert payload["runtime"]["decision_id"] == "lad_checkout_post_pay_20260418t120010z"
    assert payload["runtime"]["report_id"] == "rpt_checkout_post_api_pay_20260418t120008z"
    assert payload["runtime"]["investigation_stage"] == "cloud_fallback"

    metadata_store = MetadataStore(db_path=tmp_path / "metadata.sqlite3")
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")
    artifact_store = JSONLArtifactStore(root=tmp_path)

    assert [record["artifact_id"] for record in metadata_store.list_artifacts("alert_reports")] == [
        "rpt_checkout_post_api_pay_20260418t120008z"
    ]
    assert {hit.doc_id for hit in search_documents(retrieval_index, "timeout", service="checkout")} >= {
        "rpt_checkout_post_api_pay_20260418t120008z"
    }
    delivery_records = artifact_store.read_all("deliveries")
    assert [record["delivery_class"] for record in delivery_records] == ["page_owner"]
    assert [record["route_adapter"] for record in delivery_records] == ["adapter_feishu"]
    assert [record["delivery_mode"] for record in delivery_records] == ["env_gated_live"]
    assert [record["status"] for record in delivery_records] == ["deferred"]
    assert [record["env_gate_state"] for record in delivery_records] == ["missing_env"]



def test_create_app_exposes_health_and_readiness_routes(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path, evidence_source="live"))

    health = client.get("/healthz")
    readiness = client.get("/readyz")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "warning-agent",
        "surface": "alertmanager_webhook",
    }
    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "ready",
        "service": "warning-agent",
        "surface": "alertmanager_webhook",
        "evidence_source": "live",
        "checks": {
            "repo_root_exists": True,
            "thresholds_config_exists": True,
            "escalation_config_exists": True,
        },
        "integration_baseline": {
            "schema_version": "integration-rollout-baseline.v1",
            "surface": "warning-agent",
            "operator_paths": {
                "health": "/healthz",
                "readiness": "/readyz",
                "outcome_admit": "/outcome/admit",
            },
            "outcome_admission": {
                "status": "ready",
                "route_path": "/outcome/admit",
                "receipt_schema_version": "outcome-admission-receipt.v1",
                "artifact_root": str(tmp_path),
                "metadata_db_path": str(tmp_path / "metadata.sqlite3"),
                "retrieval_db_path": str(tmp_path / "retrieval" / "retrieval.sqlite3"),
            },
            "delivery_bridge": {
                "delivery_class": "page_owner",
                "route_adapter": "adapter_feishu",
                "delivery_mode": "env_gated_live",
                "provider_key": "warning-agent",
                "env_gate_state": "missing_env",
                "missing_env": [
                    "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",
                    "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
                    "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
                ],
                "live_endpoint": None,
                "endpoint_env": "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",
                "target_env": {
                    "chat_id_env": "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
                    "open_id_env": "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
                    "thread_id_env": "WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID",
                },
            },
            "provider_runtime": {
                "local_primary": {
                    "mode": "deterministic_smoke",
                    "smoke_model_provider": "local_vllm",
                    "smoke_model_name": "local-primary-smoke",
                    "real_adapter": "local_vllm_openai_compat",
                    "transport": "openai_compatible_http",
                    "enabled_env": "WARNING_AGENT_LOCAL_PRIMARY_REAL_ADAPTER_ENABLED",
                    "gate_state": "smoke_default",
                    "missing_env": [],
                    "model_name": None,
                    "endpoint": None,
                    "fail_closed_action": "send_to_human_review",
                },
                "cloud_fallback": {
                    "mode": "deterministic_smoke",
                    "smoke_model_provider": "openai",
                    "smoke_model_name": "cloud-fallback-smoke",
                    "real_adapter": "openai_responses_api",
                    "transport": "openai_responses_api",
                    "enabled_env": "WARNING_AGENT_CLOUD_FALLBACK_REAL_ADAPTER_ENABLED",
                    "gate_state": "smoke_default",
                    "missing_env": [],
                    "model_name": None,
                    "endpoint": None,
                    "fail_closed_action": "send_to_human_review",
                },
            },
        },
    }



def test_webhook_returns_explicit_error_receipt_for_missing_fixture(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))
    payload = copy.deepcopy(_load_alert_payload())
    payload["commonLabels"]["service"] = "missing-service"
    payload["alerts"][0]["labels"]["service"] = "missing-service"

    response = client.post(WEBHOOK_PATH, json=payload)

    assert response.status_code == 422
    assert response.json()["schema_version"] == "alertmanager-webhook-receipt.v1"
    assert response.json()["accepted"] is False
    assert response.json()["receipt_state"] == "rejected"
    assert response.json()["normalized"]["service"] == "missing-service"
    assert response.json()["error"]["code"] == "runtime_validation_error"
    assert "webhook evidence fixture does not exist" in response.json()["error"]["message"]



def test_webhook_runtime_path_materializes_feishu_bridge_payload_when_env_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)
    monkeypatch.setattr(
        "app.delivery.runtime.post_adapter_feishu_notification",
        lambda endpoint, payload, timeout_seconds: BridgeDispatchResult(
            status="delivered",
            response_code=202,
            provider_key="warning-agent",
            provider_status="delivered",
            message=None,
            external_ref="msg-1",
            raw_response={"code": 0, "providerKey": "warning-agent", "status": "delivered"},
        ),
    )
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(WEBHOOK_PATH, json=_load_alert_payload())

    assert response.status_code == 200
    artifact_store = JSONLArtifactStore(root=tmp_path)
    delivery_records = artifact_store.read_all("deliveries")
    assert [record["route_adapter"] for record in delivery_records] == ["adapter_feishu"]
    assert [record["delivery_mode"] for record in delivery_records] == ["env_gated_live"]
    assert [record["status"] for record in delivery_records] == ["delivered"]
    assert [record["env_gate_state"] for record in delivery_records] == ["ready"]
    assert delivery_records[0]["response_code"] == 202
    assert delivery_records[0]["provider_key"] == "warning-agent"
    assert delivery_records[0]["provider_status"] == "delivered"
    assert delivery_records[0]["external_ref"] == "msg-1"
    assert delivery_records[0]["target_ref"] == "oc-test-chat"
    assert delivery_records[0]["live_endpoint"] == "http://127.0.0.1:8787/providers/webhook"
    assert Path(delivery_records[0]["bridge_payload_path"]).exists()



def test_webhook_runtime_path_persists_non_empty_retrieval_hits_when_outcomes_exist(tmp_path: Path) -> None:
    _seed_checkout_outcome_retrieval(tmp_path)
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(WEBHOOK_PATH, json=_load_alert_payload())

    assert response.status_code == 200
    artifact_store = JSONLArtifactStore(root=tmp_path)
    decision_records = artifact_store.read_all("decisions")
    assert decision_records[0]["retrieval_hits"] == [
        {
            "packet_id": "ipk_checkout_reference_20260417t090000z",
            "similarity": 0.9,
            "known_outcome": "severe",
        }
    ]
