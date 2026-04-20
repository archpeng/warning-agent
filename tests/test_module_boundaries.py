from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]



def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")



def test_analyzer_training_and_runtime_surfaces_are_split_by_helper_modules() -> None:
    trained_scorer = _read("app/analyzer/trained_scorer.py")
    calibrate = _read("app/analyzer/calibrate.py")

    assert "from app.analyzer.trained_scorer_runtime import" in trained_scorer
    assert "from app.analyzer.trained_scorer_training import train_trained_scorer_artifact" in trained_scorer
    assert "from app.analyzer.corpus_packets import build_manual_replay_packet" in calibrate



def test_investigator_internal_splits_are_routed_through_narrow_helper_modules() -> None:
    local_primary = _read("app/investigator/local_primary.py")
    cloud_fallback = _read("app/investigator/cloud_fallback.py")
    responses = _read("app/investigator/cloud_fallback_openai_responses.py")

    assert "from app.investigator.local_primary_resident import" in local_primary
    assert "from app.investigator.cloud_fallback_brief import" in cloud_fallback
    assert "from app.investigator.cloud_fallback_brief import" in responses



def test_normalized_alert_contract_is_shared_outside_webhook_implementation() -> None:
    packet_builder = _read("app/packet/builder.py")
    webhook = _read("app/receiver/alertmanager_webhook.py")
    signoz_alert = _read("app/receiver/signoz_alert.py")

    assert "from app.receiver.contracts import NormalizedAlertGroup" in packet_builder
    assert "from app.receiver.contracts import NormalizedAlertGroup" in webhook
    assert "from app.receiver.contracts import NormalizedAlertGroup, NormalizedSourceRefs" in signoz_alert
