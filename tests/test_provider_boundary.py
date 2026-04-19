from __future__ import annotations

from pathlib import Path

from app.investigator.provider_boundary import load_provider_boundary_config


REPO_ROOT = Path(__file__).resolve().parents[1]



def test_provider_boundary_config_freezes_deterministic_smoke_and_fail_closed_rule() -> None:
    config = load_provider_boundary_config(REPO_ROOT / "configs" / "provider-boundary.yaml")

    assert config.local_primary.mode == "deterministic_smoke"
    assert config.local_primary.fail_closed_recommended_action == "send_to_human_review"
    assert config.cloud_fallback.mode == "deterministic_smoke"
    assert config.cloud_fallback.fail_closed_recommended_action == "send_to_human_review"
