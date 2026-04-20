"""Operator-visible rollout evidence baseline for external integration surfaces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from app.contracts_common import DATA_DIR

INTEGRATION_BASELINE_SCHEMA_VERSION = "integration-rollout-baseline.v1"
INTEGRATION_EVIDENCE_SCHEMA_VERSION = "integration-rollout-evidence.v1"
HEALTH_PATH = "/healthz"
READINESS_PATH = "/readyz"
OUTCOME_ADMIT_PATH = "/outcome/admit"



def _resolve_data_root(data_root: str | Path | None) -> Path:
    return Path(data_root) if data_root is not None else DATA_DIR



def _build_outcome_admission_baseline(*, data_root: Path) -> dict[str, object]:
    return {
        "status": "ready",
        "route_path": OUTCOME_ADMIT_PATH,
        "receipt_schema_version": "outcome-admission-receipt.v1",
        "artifact_root": str(data_root),
        "metadata_db_path": str(data_root / "metadata.sqlite3"),
        "retrieval_db_path": str(data_root / "retrieval" / "retrieval.sqlite3"),
    }



def _build_delivery_bridge_baseline(*, repo_root: Path, env: Mapping[str, str | None]) -> dict[str, object]:
    from app.delivery.env_gate import resolve_adapter_feishu_env_gate
    from app.delivery.runtime import EnvGatedLiveRoute, build_delivery_governance_snapshot, load_delivery_config

    config = load_delivery_config(repo_root / "configs" / "delivery.yaml")
    route = config.routes["page_owner"]
    if not isinstance(route, EnvGatedLiveRoute):
        raise ValueError("page_owner delivery route must remain env-gated live for W6 rollout evidence")

    resolution = resolve_adapter_feishu_env_gate(route, env=env)
    live_endpoint = f"{resolution.endpoint}/providers/webhook" if resolution.endpoint is not None else None
    return {
        "delivery_class": route.delivery_class,
        "route_adapter": route.adapter,
        "delivery_mode": route.delivery_mode,
        "provider_key": route.provider_key,
        "env_gate_state": resolution.state,
        "missing_env": list(resolution.missing_env),
        "live_endpoint": live_endpoint,
        "endpoint_env": route.endpoint_env,
        "target_env": {
            "chat_id_env": route.target.chat_id_env,
            "open_id_env": route.target.open_id_env,
            "thread_id_env": route.target.thread_id_env,
        },
        "governance": build_delivery_governance_snapshot(repo_root / "configs" / "delivery.yaml"),
    }



def _build_local_primary_abnormal_path_policy() -> dict[str, object]:
    return {
        "direct_runtime": {
            "not_ready": "fallback_to_cloud_fallback",
            "degraded": "fallback_to_cloud_fallback",
        },
        "warning_worker": {
            "not_ready": "fallback_to_cloud_fallback",
            "degraded": "queue_wait_for_local_primary_recovery",
        },
    }



def _build_provider_gate_baseline(
    boundary,
    *,
    env: Mapping[str, str | None],
    budget_contract: dict[str, object] | None = None,
    resident_lifecycle: dict[str, object] | None = None,
    abnormal_path_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    from app.investigator.provider_boundary import resolve_real_adapter_gate

    gate = resolve_real_adapter_gate(boundary, env=env)
    payload = {
        "mode": boundary.mode,
        "smoke_model_provider": boundary.smoke.model_provider,
        "smoke_model_name": boundary.smoke.model_name,
        "operating_contract": {
            "provider_role": boundary.operating_contract.provider_role,
            "target_model_provider": boundary.operating_contract.target_model_provider,
            "target_model_name": boundary.operating_contract.target_model_name,
            "service_mode": boundary.operating_contract.service_mode,
            "invocation_scope": boundary.operating_contract.invocation_scope,
            "readiness_source": boundary.operating_contract.readiness_source,
            "ready_action": boundary.operating_contract.ready_action,
            "not_ready_action": boundary.operating_contract.not_ready_action,
            "degraded_action": boundary.operating_contract.degraded_action,
            "fallback_provider": boundary.operating_contract.fallback_provider,
            "queue_policy": boundary.operating_contract.queue_policy,
        },
        "real_adapter": boundary.real_adapter.adapter,
        "transport": boundary.real_adapter.transport,
        "enabled_env": boundary.real_adapter.enabled_env,
        "gate_state": gate.state,
        "missing_env": list(gate.missing_env),
        "model_name": gate.model_name,
        "endpoint": gate.endpoint,
        "fail_closed_action": boundary.fail_closed_recommended_action,
    }
    if budget_contract is not None:
        payload["budget_contract"] = budget_contract
    if resident_lifecycle is not None:
        payload["resident_lifecycle"] = resident_lifecycle
    if abnormal_path_policy is not None:
        payload["abnormal_path_policy"] = abnormal_path_policy
    return payload



def _build_signoz_warning_plane_baseline(*, data_root: Path, env: Mapping[str, str | None]) -> dict[str, object]:
    from app.receiver.signoz_ingress import (
        SIGNOZ_CALLER_HEADER,
        SIGNOZ_INGRESS_PATH,
        SIGNOZ_INGRESS_RECEIPT_SCHEMA_VERSION,
        resolve_signoz_ingress_auth,
    )
    from app.receiver.signoz_queue import build_signoz_warning_queue_governance
    from app.storage.signoz_warning_store import SignozWarningStore

    warning_store = SignozWarningStore(root=data_root)
    auth = resolve_signoz_ingress_auth(env={k: v for k, v in env.items() if isinstance(v, str)})
    return {
        "route_path": SIGNOZ_INGRESS_PATH,
        "receipt_schema_version": SIGNOZ_INGRESS_RECEIPT_SCHEMA_VERSION,
        "caller_header": SIGNOZ_CALLER_HEADER,
        "auth_mode": "shared_token",
        "auth_state": auth.state,
        "shared_token_env": auth.shared_token_env,
        "artifact_root": str(warning_store.warning_root),
        "index_db_path": str(warning_store.db_path),
        "queue": warning_store.queue_metrics(),
        "governance": build_signoz_warning_queue_governance(),
    }



def _build_local_primary_budget_contract(config) -> dict[str, object]:
    budget = config.local_primary.budget
    budget_contract = config.local_primary.budget_contract
    return {
        "profile": budget_contract.profile,
        "scope": budget_contract.scope,
        "startup_cost_policy": budget_contract.startup_cost_policy,
        "caps": {
            "wall_time_seconds": budget.wall_time_seconds,
            "max_tool_calls": budget.max_tool_calls,
            "max_prompt_tokens": budget.max_prompt_tokens,
            "max_completion_tokens": budget.max_completion_tokens,
            "max_retrieval_refs": budget.max_retrieval_refs,
            "max_trace_refs": budget.max_trace_refs,
            "max_log_refs": budget.max_log_refs,
            "max_code_refs": budget.max_code_refs,
        },
    }


def build_integration_baseline(
    *,
    repo_root: str | Path = Path("."),
    data_root: str | Path | None = None,
    env: Mapping[str, str | None] = os.environ,
) -> dict[str, object]:
    from app.investigator.local_primary import (
        local_primary_resident_lifecycle_payload,
        prewarm_local_primary_resident_service,
    )
    from app.investigator.provider_boundary import load_provider_boundary_config
    from app.investigator.router import load_investigator_routing_config
    from app.receiver.signoz_ingress import SIGNOZ_INGRESS_PATH

    repo_root = Path(repo_root)
    data_root = _resolve_data_root(data_root)
    boundary = load_provider_boundary_config(repo_root / "configs" / "provider-boundary.yaml")
    routing = load_investigator_routing_config(repo_root / "configs" / "escalation.yaml")
    local_primary_resident = prewarm_local_primary_resident_service(
        config_path=repo_root / "configs" / "escalation.yaml",
        repo_root=repo_root,
        env=env,
    )

    from app.feedback.governance import feedback_governance_payload, load_feedback_governance_config

    return {
        "schema_version": INTEGRATION_BASELINE_SCHEMA_VERSION,
        "surface": "warning-agent",
        "operator_paths": {
            "health": HEALTH_PATH,
            "readiness": READINESS_PATH,
            "outcome_admit": OUTCOME_ADMIT_PATH,
            "signoz_ingress": SIGNOZ_INGRESS_PATH,
        },
        "outcome_admission": _build_outcome_admission_baseline(data_root=data_root),
        "signoz_warning_plane": _build_signoz_warning_plane_baseline(data_root=data_root, env=env),
        "delivery_bridge": _build_delivery_bridge_baseline(repo_root=repo_root, env=env),
        "feedback_loop": feedback_governance_payload(
            load_feedback_governance_config(repo_root / "configs" / "feedback-governance.yaml")
        ),
        "provider_runtime": {
            "local_primary": _build_provider_gate_baseline(
                boundary.local_primary,
                env=env,
                budget_contract=_build_local_primary_budget_contract(routing),
                resident_lifecycle=local_primary_resident_lifecycle_payload(local_primary_resident.lifecycle),
                abnormal_path_policy=_build_local_primary_abnormal_path_policy(),
            ),
            "cloud_fallback": _build_provider_gate_baseline(boundary.cloud_fallback, env=env),
        },
    }



def persist_integration_rollout_evidence(
    *,
    artifact_root: Path,
    repo_root: str | Path,
    data_root: str | Path | None,
    packet_id: str,
    decision_id: str,
    report_id: str,
    generated_at: str,
    env: Mapping[str, str | None] = os.environ,
) -> Path:
    baseline = build_integration_baseline(repo_root=repo_root, data_root=data_root, env=env)
    payload = {
        "schema_version": INTEGRATION_EVIDENCE_SCHEMA_VERSION,
        "packet_id": packet_id,
        "decision_id": decision_id,
        "report_id": report_id,
        "generated_at": generated_at,
        "integration_baseline": baseline,
    }
    path = artifact_root / "rollout_evidence" / f"{packet_id}.integration-rollout-evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
