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
    from app.delivery.runtime import EnvGatedLiveRoute, load_delivery_config

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
    }



def _build_provider_gate_baseline(boundary, *, env: Mapping[str, str | None]) -> dict[str, object]:
    from app.investigator.provider_boundary import resolve_real_adapter_gate

    gate = resolve_real_adapter_gate(boundary, env=env)
    return {
        "mode": boundary.mode,
        "smoke_model_provider": boundary.smoke.model_provider,
        "smoke_model_name": boundary.smoke.model_name,
        "real_adapter": boundary.real_adapter.adapter,
        "transport": boundary.real_adapter.transport,
        "enabled_env": boundary.real_adapter.enabled_env,
        "gate_state": gate.state,
        "missing_env": list(gate.missing_env),
        "model_name": gate.model_name,
        "endpoint": gate.endpoint,
        "fail_closed_action": boundary.fail_closed_recommended_action,
    }



def build_integration_baseline(
    *,
    repo_root: str | Path = Path("."),
    data_root: str | Path | None = None,
    env: Mapping[str, str | None] = os.environ,
) -> dict[str, object]:
    from app.investigator.provider_boundary import load_provider_boundary_config

    repo_root = Path(repo_root)
    data_root = _resolve_data_root(data_root)
    boundary = load_provider_boundary_config(repo_root / "configs" / "provider-boundary.yaml")

    return {
        "schema_version": INTEGRATION_BASELINE_SCHEMA_VERSION,
        "surface": "warning-agent",
        "operator_paths": {
            "health": HEALTH_PATH,
            "readiness": READINESS_PATH,
            "outcome_admit": OUTCOME_ADMIT_PATH,
        },
        "outcome_admission": _build_outcome_admission_baseline(data_root=data_root),
        "delivery_bridge": _build_delivery_bridge_baseline(repo_root=repo_root, env=env),
        "provider_runtime": {
            "local_primary": _build_provider_gate_baseline(boundary.local_primary, env=env),
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
