"""Replay/evidence corpus packet materialization helpers for analyzer training and benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture



def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))



def build_manual_replay_packet(
    *,
    repo_root: Path,
    replay_fixture: str | Path,
    evidence_fixture: str | Path,
) -> dict[str, object]:
    replay = load_manual_replay_fixture(repo_root / replay_fixture)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    evidence = _load_json(repo_root / evidence_fixture)
    return build_incident_packet_from_bundle(normalized, evidence)
