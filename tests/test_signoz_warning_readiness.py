from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.receiver.alertmanager_webhook import create_app
from app.receiver.signoz_ingress import SIGNOZ_CALLER_HEADER, SIGNOZ_INGRESS_PATH, SIGNOZ_SHARED_TOKEN_ENV
from app.receiver.signoz_worker import run_signoz_worker_once
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



def test_readyz_exposes_signoz_warning_auth_queue_and_provider_contract_truth(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(SIGNOZ_SHARED_TOKEN_ENV, "secret-token")
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path, evidence_source="live"))

    first = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())
    second = client.post(SIGNOZ_INGRESS_PATH, json=_load_signoz_payload(), headers=_headers())
    first_warning_id = first.json()["warning_id"]
    assert second.json()["queue"]["queue_state"] == "deduped"

    store = SignozWarningStore(root=tmp_path)
    run_signoz_worker_once(
        store=store,
        now="2026-04-20T13:00:00Z",
        processor=lambda warning_id: {
            "packet_id": f"ipk_{warning_id}",
            "decision_id": f"lad_{warning_id}",
            "report_id": f"rpt_{warning_id}",
            "investigation_stage": "cloud_fallback",
            "delivery_status": "deferred",
            "evidence_state": "partial",
            "human_review_required": True,
            "recommended_action": "send_to_human_review",
            "runtime_artifacts": {
                "packet_path": str(tmp_path / "packet.json"),
                "decision_path": str(tmp_path / "decision.json"),
                "investigation_path": None,
                "report_path": str(tmp_path / "report.md"),
                "delivery_dispatches_path": None,
                "metadata_db_path": None,
                "retrieval_db_path": None,
                "rollout_evidence_path": None,
            },
        },
    )

    readiness = client.get("/readyz")

    assert readiness.status_code == 200
    payload = readiness.json()["integration_baseline"]
    queue = payload["signoz_warning_plane"]["queue"]
    assert payload["signoz_warning_plane"]["auth_state"] == "ready"
    assert payload["signoz_warning_plane"]["governance"]["state_actions"]["waiting_local_primary_recovery"] == "retry_after_local_recovery_window"
    assert queue == {
        "queue_states": {
            "pending": 0,
            "processing": 0,
            "waiting_local_primary_recovery": 0,
            "completed": 1,
            "failed": 0,
            "dead_letter": 0,
            "deduped": 1,
        },
        "backlog_size": 0,
        "oldest_pending_age_sec": None,
        "oldest_local_primary_recovery_wait_age_sec": None,
        "processing_failure_count": 0,
        "local_primary_recovery_wait_count": 0,
        "delivery_deferred_count": 1,
        "cloud_fallback_ratio": 1.0,
    }
    assert payload["provider_runtime"]["local_primary"]["operating_contract"]["not_ready_action"] == "fallback_or_queue"
    assert payload["provider_runtime"]["local_primary"]["operating_contract"]["queue_policy"] == "wait_for_local_primary_recovery"
    assert payload["provider_runtime"]["local_primary"]["budget_contract"]["profile"] == "resident_26b_high_budget"
    assert payload["provider_runtime"]["local_primary"]["budget_contract"]["caps"]["wall_time_seconds"] == 300
    assert payload["provider_runtime"]["local_primary"]["resident_lifecycle"]["state"] == "ready"
    assert (
        payload["provider_runtime"]["local_primary"]["abnormal_path_policy"]["warning_worker"]["degraded"]
        == "queue_wait_for_local_primary_recovery"
    )
    assert payload["provider_runtime"]["cloud_fallback"]["operating_contract"]["target_model_provider"] == "neko_api_openai"
    assert payload["feedback_loop"]["promotion"]["minimum_landed_outcome_cases"] == 3
    assert store.get_warning_row(first_warning_id)["queue_state"] == "completed"
