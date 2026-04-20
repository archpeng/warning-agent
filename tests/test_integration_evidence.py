from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import build_runtime_entrypoint
from app.receiver.alertmanager_webhook import WEBHOOK_PATH, create_app
from app.runtime_entry import build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"



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
    }
    assert baseline["outcome_admission"]["status"] == "ready"
    assert baseline["outcome_admission"]["receipt_schema_version"] == "outcome-admission-receipt.v1"
    assert baseline["delivery_bridge"]["route_adapter"] == "adapter_feishu"
    assert baseline["delivery_bridge"]["env_gate_state"] == "missing_env"
    assert baseline["delivery_bridge"]["provider_key"] == "warning-agent"
    assert baseline["provider_runtime"]["local_primary"]["gate_state"] == "smoke_default"
    assert baseline["provider_runtime"]["local_primary"]["fail_closed_action"] == "send_to_human_review"
    assert baseline["provider_runtime"]["cloud_fallback"]["gate_state"] == "smoke_default"



def test_readyz_returns_integration_baseline_details(tmp_path: Path) -> None:
    client = TestClient(create_app(repo_root=REPO_ROOT, data_root=tmp_path))

    readiness = client.get("/readyz")

    assert readiness.status_code == 200
    payload = readiness.json()
    assert payload["status"] == "ready"
    assert payload["integration_baseline"]["schema_version"] == "integration-rollout-baseline.v1"
    assert payload["integration_baseline"]["delivery_bridge"]["env_gate_state"] == "missing_env"
    assert payload["integration_baseline"]["provider_runtime"]["local_primary"]["gate_state"] == "smoke_default"
    assert payload["integration_baseline"]["provider_runtime"]["cloud_fallback"]["gate_state"] == "smoke_default"



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
