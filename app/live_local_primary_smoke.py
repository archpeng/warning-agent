"""Optional env-opt smoke helper for the local-primary real adapter seam."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.investigator.runtime import run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


DEFAULT_REPLAY_FIXTURE = Path("fixtures/replay/manual-replay.checkout.high-error-rate.json")
DEFAULT_EVIDENCE_FIXTURE = Path("fixtures/evidence/checkout.packet-input.json")
DEFAULT_DECISION_FIXTURE = Path("fixtures/evidence/checkout.local-decision.json")



def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



def run_live_local_primary_adapter_smoke(
    *,
    repo_root: str | Path = Path("."),
    replay_fixture: str | Path = DEFAULT_REPLAY_FIXTURE,
    evidence_fixture: str | Path = DEFAULT_EVIDENCE_FIXTURE,
    decision_fixture: str | Path = DEFAULT_DECISION_FIXTURE,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    replay_fixture = repo_root / Path(replay_fixture)
    evidence_fixture = repo_root / Path(evidence_fixture)
    decision_fixture = repo_root / Path(decision_fixture)

    replay = load_manual_replay_fixture(replay_fixture)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    packet = build_incident_packet_from_bundle(normalized, _load_json(evidence_fixture))
    decision = _load_json(decision_fixture)
    execution = run_investigation_runtime(
        packet,
        decision,
        config_path=repo_root / "configs" / "escalation.yaml",
        repo_root=repo_root,
    )
    final_result = execution.final_result
    if final_result is None:
        raise RuntimeError("local-primary smoke expected an investigation result but runtime returned none")

    return {
        "packet_id": packet["packet_id"],
        "decision_id": decision["decision_id"],
        "investigator_tier": final_result["investigator_tier"],
        "model_provider": final_result["model_provider"],
        "model_name": final_result["model_name"],
        "summary": final_result["summary"],
        "unknowns": final_result["unknowns"],
        "analysis_notes": final_result["analysis_updates"]["notes"],
        "cloud_escalated": execution.cloud_plan.should_escalate if execution.cloud_plan else False,
    }
