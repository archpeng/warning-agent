"""Live-data MVP smoke helpers for warning-agent."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector
from app.runtime_entry import RuntimeEntrypoint, build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


def run_live_runtime_smoke(
    replay_fixture: str | Path,
    *,
    repo_root: str | Path = Path("."),
    artifact_store: JSONLArtifactStore | None = None,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    replay_fixture = Path(replay_fixture)
    if not replay_fixture.is_absolute():
        replay_fixture = (repo_root / replay_fixture).resolve()

    entrypoint = RuntimeEntrypoint(
        mode="replay",
        replay_fixture=replay_fixture,
        evidence_source="live",
    )
    execution = execute_runtime_entrypoint(
        entrypoint,
        repo_root=repo_root,
        artifact_store=artifact_store,
        prometheus_collector=prometheus_collector,
        signoz_collector=signoz_collector,
        evidence_now=evidence_now,
    )
    summary = build_runtime_execution_summary(execution)

    return {
        "entrypoint": {
            "mode": entrypoint.mode,
            "replay_fixture": str(entrypoint.replay_fixture),
            "evidence_source": entrypoint.evidence_source,
        },
        "runtime": asdict(summary),
        "packet_service": execution.packet["service"],
        "packet_operation": execution.packet.get("operation"),
        "persisted": execution.persisted_artifacts is not None,
        "evidence_fixture": str(execution.evidence_fixture) if execution.evidence_fixture else None,
    }
