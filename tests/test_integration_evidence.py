from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import build_runtime_entrypoint
from app.receiver.alertmanager_webhook import WEBHOOK_PATH, create_app
from app.runtime_entry import build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


@pytest.fixture(autouse=True)
def _reset_local_primary_resident_runtime() -> None:
    from app.investigator.local_primary import reset_local_primary_resident_service

    reset_local_primary_resident_service()
    yield
    reset_local_primary_resident_service()



def _load_alert_payload() -> dict:
    with REPLAY_FIXTURE.open("r", encoding="utf-8") as handle:
        envelope = json.load(handle)
    return envelope["alert_payload"]



def test_build_integration_baseline_reports_operator_visible_gate_truth(tmp_path: Path) -> None:
    from app.integration_evidence import build_integration_baseline

    baseline = build_integration_baseline(repo_root=REPO_ROOT, data_root=tmp_path, env={})

    assert baseline["schema_version"] == "integration-rollout-baseline.v1"
    assert baseline["surface"] == "warning-agent"
    assert baseline["operator_paths"] == {
        "health": "/healthz",
        "readiness": "/readyz",
        "outcome_admit": "/outcome/admit",
        "signoz_ingress": "/webhook/signoz",
    }
    assert baseline["outcome_admission"]["status"] == "ready"
    assert baseline["outcome_admission"]["receipt_schema_version"] == "outcome-admission-receipt.v1"
    assert baseline["signoz_warning_plane"]["route_path"] == "/webhook/signoz"
    assert baseline["signoz_warning_plane"]["auth_state"] == "missing_env"
    assert baseline["signoz_warning_plane"]["queue"]["backlog_size"] == 0
    assert baseline["signoz_warning_plane"]["governance"] == {
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
    assert baseline["delivery_bridge"]["route_adapter"] == "adapter_feishu"
    assert baseline["delivery_bridge"]["env_gate_state"] == "missing_env"
    assert baseline["delivery_bridge"]["governance"]["delivery_plane"] == "warning-agent"
    assert baseline["provider_runtime"]["local_primary"]["gate_state"] == "smoke_default"
    assert baseline["provider_runtime"]["local_primary"]["fail_closed_action"] == "send_to_human_review"
    assert baseline["provider_runtime"]["local_primary"]["operating_contract"] == {
        "provider_role": "primary_local_investigator",
        "target_model_provider": "gemma4",
        "target_model_name": "gemma4-26b",
        "service_mode": "resident_prewarm_on_boot",
        "invocation_scope": "needs_investigation_only",
        "readiness_source": "resident_service",
        "ready_action": "invoke_when_needed",
        "not_ready_action": "fallback_or_queue",
        "degraded_action": "fallback_or_queue",
        "fallback_provider": "cloud_fallback",
        "queue_policy": "wait_for_local_primary_recovery",
    }
    assert baseline["provider_runtime"]["local_primary"]["budget_contract"] == {
        "profile": "resident_26b_high_budget",
        "scope": "per_investigation_when_resident_ready",
        "startup_cost_policy": "excluded_from_per_warning_budget",
        "caps": {
            "wall_time_seconds": 300,
            "max_tool_calls": 16,
            "max_prompt_tokens": 12000,
            "max_completion_tokens": 2400,
            "max_retrieval_refs": 16,
            "max_trace_refs": 8,
            "max_log_refs": 8,
            "max_code_refs": 8,
        },
    }
    assert baseline["provider_runtime"]["local_primary"]["resident_lifecycle"] == {
        "service_mode": "resident_prewarm_on_boot",
        "invocation_scope": "needs_investigation_only",
        "startup_cost_policy": "excluded_from_per_warning_budget",
        "provider_mode": "smoke_resident",
        "state": "ready",
        "gate_state": "smoke_default",
        "model_name": "local-primary-smoke",
        "prewarm_completed_once": True,
        "prewarm_attempt_count": 1,
        "prewarm_source": "provider_init",
        "reason": "smoke-default resident local-primary requires no external warmup",
    }
    assert baseline["provider_runtime"]["local_primary"]["abnormal_path_policy"] == {
        "direct_runtime": {
            "not_ready": "fallback_to_cloud_fallback",
            "degraded": "fallback_to_cloud_fallback",
        },
        "warning_worker": {
            "not_ready": "fallback_to_cloud_fallback",
            "degraded": "queue_wait_for_local_primary_recovery",
        },
    }
    assert baseline["feedback_loop"]["promotion"]["minimum_landed_outcome_cases"] == 3
    assert baseline["feedback_loop"]["rollback"]["rollback_to_previous_runtime_artifact"] is True
    assert baseline["provider_runtime"]["cloud_fallback"]["gate_state"] == "smoke_default"
    assert baseline["provider_runtime"]["cloud_fallback"]["operating_contract"] == {
        "provider_role": "sparse_cloud_fallback",
        "target_model_provider": "neko_api_openai",
        "target_model_name": "gpt-5.4-xhigh",
        "service_mode": "env_gated_remote",
        "invocation_scope": "fallback_only",
        "readiness_source": "env_gate",
        "ready_action": "invoke_when_selected",
        "not_ready_action": "fail_closed",
        "degraded_action": "fail_closed",
        "fallback_provider": None,
        "queue_policy": None,
    }



def test_readyz_returns_integration_baseline_details(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    readiness = client.get("/readyz")

    assert readiness.status_code == 200
    payload = readiness.json()
    assert payload["status"] == "ready"
    assert payload["integration_baseline"]["schema_version"] == "integration-rollout-baseline.v1"
    assert payload["integration_baseline"]["delivery_bridge"]["env_gate_state"] == "missing_env"
    assert payload["integration_baseline"]["signoz_warning_plane"]["governance"]["queue_mode"] == "strict_serial_warning_plane"
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["gate_state"] == "smoke_default"
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["operating_contract"]["target_model_name"] == "gemma4-26b"
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["budget_contract"]["caps"]["max_prompt_tokens"] == 12000
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["resident_lifecycle"]["state"] == "ready"
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["abnormal_path_policy"]["warning_worker"]["degraded"] == "queue_wait_for_local_primary_recovery"
    assert payload["integration_baseline"]["provider_runtime"]["cloud_fallback"]["gate_state"] == "smoke_default"
    assert payload["integration_baseline"]["provider_runtime"]["cloud_fallback"]["operating_contract"]["target_model_name"] == "gpt-5.4-xhigh"
    assert payload["integration_baseline"]["feedback_loop"]["promotion"]["minimum_landed_outcome_cases"] == 3



def test_execute_runtime_entrypoint_persists_machine_readable_rollout_evidence(tmp_path: Path) -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )
    store = JSONLArtifactStore(root=tmp_path)

    execution = execute_runtime_entrypoint(entrypoint, repo_root=REPO_ROOT, artifact_store=store)

    assert execution.persisted_artifacts is not None
    assert execution.persisted_artifacts.rollout_evidence_path is not None
    assert execution.persisted_artifacts.rollout_evidence_path.exists()

    evidence = json.loads(execution.persisted_artifacts.rollout_evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "integration-rollout-evidence.v1"
    assert evidence["packet_id"] == execution.packet["packet_id"]
    assert evidence["decision_id"] == execution.decision["decision_id"]
    assert evidence["report_id"] == "rpt_checkout_post_api_pay_20260418t120008z"
    assert evidence["integration_baseline"]["delivery_bridge"]["env_gate_state"] == "missing_env"
    assert evidence["integration_baseline"]["provider_runtime"]["local_primary"]["gate_state"] == "smoke_default"
    assert (
        evidence["integration_baseline"]["provider_runtime"]["local_primary"]["operating_contract"]["not_ready_action"]
        == "fallback_or_queue"
    )
    assert (
        evidence["integration_baseline"]["provider_runtime"]["local_primary"]["budget_contract"]["startup_cost_policy"]
        == "excluded_from_per_warning_budget"
    )
    assert evidence["integration_baseline"]["provider_runtime"]["local_primary"]["resident_lifecycle"]["state"] == "ready"

    runtime_summary = build_runtime_execution_summary(execution)
    assert runtime_summary.rollout_evidence_path == str(execution.persisted_artifacts.rollout_evidence_path)



def test_webhook_receipt_exposes_rollout_evidence_path(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    response = client.post(WEBHOOK_PATH, json=_load_alert_payload())

    assert response.status_code == 200
    receipt = response.json()
    rollout_evidence_path = Path(receipt["runtime"]["rollout_evidence_path"])
    assert rollout_evidence_path.exists()

    evidence = json.loads(rollout_evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "integration-rollout-evidence.v1"
    assert evidence["report_id"] == receipt["runtime"]["report_id"]
    assert evidence["integration_baseline"]["outcome_admission"]["status"] == "ready"
    assert evidence["integration_baseline"]["provider_runtime"]["cloud_fallback"]["operating_contract"]["target_model_name"] == "gpt-5.4-xhigh"
    assert evidence["integration_baseline"]["signoz_warning_plane"]["governance"]["queue_mode"] == "strict_serial_warning_plane"
