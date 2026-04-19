from __future__ import annotations

from pathlib import Path

from app.receiver.replay_loader import (
    MANUAL_REPLAY_PROTOCOL_VERSION,
    load_manual_replay_fixture,
    summarize_manual_replay,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


def test_manual_replay_fixture_loads() -> None:
    envelope = load_manual_replay_fixture(FIXTURE_PATH)

    assert envelope["protocol_version"] == MANUAL_REPLAY_PROTOCOL_VERSION
    assert envelope["candidate_source"] == "manual_replay"
    assert envelope["alert_payload"]["alerts"][0]["labels"]["service"] == "checkout"


def test_manual_replay_summary_exposes_routing_hints() -> None:
    envelope = load_manual_replay_fixture(FIXTURE_PATH)
    summary = summarize_manual_replay(envelope)

    assert summary == {
        "candidate_source": "manual_replay",
        "environment": "prod",
        "replay_label": "checkout-high-error-rate-fixture",
        "receiver": "warning-agent",
        "status": "firing",
        "alert_count": 1,
        "service": "checkout",
        "alertname": "HighErrorRate",
    }
