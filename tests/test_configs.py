from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(name: str) -> dict:
    with (REPO_ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_services_config_has_default_and_checkout_examples() -> None:
    payload = _load_yaml("services.yaml")

    assert set(payload["services"]).issuperset({"checkout", "default"})
    assert payload["services"]["checkout"]["owner_hint"] == "payments-oncall"


def test_thresholds_config_exposes_required_top_level_keys() -> None:
    payload = _load_yaml("thresholds.yaml")

    assert set(payload) == {
        "severity_thresholds",
        "novelty_threshold",
        "investigation_threshold",
        "confidence_threshold",
        "blast_radius_threshold",
        "minimum_calibration_cases",
        "minimum_severe_cases",
        "false_page_ceiling",
    }
    assert payload["severity_thresholds"]["P1"] > payload["severity_thresholds"]["P2"]
    assert payload["confidence_threshold"] == 0.55
    assert payload["minimum_calibration_cases"] >= payload["minimum_severe_cases"]


def test_escalation_and_report_configs_are_loadable() -> None:
    escalation = _load_yaml("escalation.yaml")
    reports = _load_yaml("reports.yaml")

    assert escalation["investigator"]["default_mode"] == "local_first"
    assert escalation["investigator"]["routing"]["allowed_provider_order"] == ["local_primary"]
    assert escalation["investigator"]["routing"]["allow_cloud_fallback"] is True
    assert escalation["investigator"]["routing"]["local_readiness_requirement"] == "resident_service"
    assert escalation["investigator"]["routing"]["local_not_ready_policy"] == "fallback_or_queue"
    assert escalation["investigator"]["routing"]["local_not_ready_fallback_provider"] == "cloud_fallback"
    assert escalation["investigator"]["routing"]["local_not_ready_queue_policy"] == "wait_for_local_primary_recovery"
    assert escalation["investigator"]["routing"]["local_degraded_policy"] == "fallback_or_queue"
    assert escalation["investigator"]["local_primary"]["model_name"] == "local-primary-smoke"
    assert escalation["investigator"]["local_primary"]["contract_target"]["model_provider"] == "gemma4"
    assert escalation["investigator"]["local_primary"]["contract_target"]["model_name"] == "gemma4-26b"
    assert escalation["investigator"]["local_primary"]["budget_contract"]["profile"] == "resident_26b_high_budget"
    assert escalation["investigator"]["local_primary"]["budget_contract"]["scope"] == "per_investigation_when_resident_ready"
    assert (
        escalation["investigator"]["local_primary"]["budget_contract"]["startup_cost_policy"]
        == "excluded_from_per_warning_budget"
    )
    assert escalation["investigator"]["local_primary"]["budgets"]["wall_time_seconds"] == 300
    assert escalation["investigator"]["local_primary"]["budgets"]["max_tool_calls"] == 16
    assert escalation["investigator"]["local_primary"]["budgets"]["max_prompt_tokens"] == 12000
    assert escalation["investigator"]["local_primary"]["budgets"]["max_completion_tokens"] == 2400
    assert escalation["investigator"]["local_primary"]["trigger_rules"]["novelty_at_or_above"] == 0.79
    assert escalation["investigator"]["local_primary"]["trigger_rules"]["severity_probability_at_or_above"] == 0.95
    assert escalation["investigator"]["local_primary"]["trigger_rules"]["blast_radius_at_or_above"] == 0.84
    assert escalation["investigator"]["local_primary"]["trigger_rules"]["page_owner_requires_confidence_below"] == 0.61
    assert escalation["investigator"]["cloud_fallback"]["enabled"] is True
    assert escalation["investigator"]["cloud_fallback"]["available_phase"] == "P5"
    assert escalation["investigator"]["cloud_fallback"]["model_provider"] == "openai"
    assert escalation["investigator"]["cloud_fallback"]["model_name"] == "cloud-fallback-smoke"
    assert escalation["investigator"]["cloud_fallback"]["contract_target"]["model_provider"] == "neko_api_openai"
    assert escalation["investigator"]["cloud_fallback"]["contract_target"]["model_name"] == "gpt-5.4-xhigh"
    assert escalation["investigator"]["cloud_fallback"]["budgets"]["max_invocation_rate_total"] == 0.05
    assert escalation["investigator"]["cloud_fallback"]["budgets"]["max_invocation_rate_investigated"] == 0.25
    assert escalation["investigator"]["cloud_fallback"]["budgets"]["max_wall_time_seconds"] == 90
    assert escalation["investigator"]["cloud_fallback"]["budgets"]["max_handoff_tokens"] == 1200
    assert escalation["investigator"]["cloud_fallback"]["audit"]["require_parent_investigation_id"] is True
    assert escalation["investigator"]["cloud_fallback"]["audit"]["require_handoff_markdown"] is True
    assert escalation["investigator"]["cloud_fallback"]["audit"]["require_handoff_tokens_estimate"] is True
    assert escalation["investigator"]["cloud_fallback"]["audit"]["require_failure_reason_note"] is True
    assert escalation["investigator"]["max_concurrent_local_primary"] >= 1
    assert escalation["investigator"]["max_concurrent_cloud_fallback"] >= 1
    assert reports["section_order"][0] == "Executive Summary"
    assert reports["severity_delivery_class"]["P1"] == "page_owner"
