from __future__ import annotations

import copy
import json
from pathlib import Path

from app.analyzer.base import load_thresholds
from app.analyzer.runtime import resolve_runtime_scorer
from app.investigator.base import build_investigation_request
from app.investigator.router import load_investigator_routing_config, plan_investigation
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_REPLAY = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
CHECKOUT_EVIDENCE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
CHECKOUT_DECISION = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
CATALOG_REPLAY = REPO_ROOT / "fixtures" / "replay" / "manual-replay.catalog.latency-warning.json"
CATALOG_EVIDENCE = REPO_ROOT / "fixtures" / "evidence" / "catalog.packet-input.json"
SEARCH_REPLAY = REPO_ROOT / "fixtures" / "replay" / "manual-replay.search.query-error-burst.json"
SEARCH_EVIDENCE = REPO_ROOT / "fixtures" / "evidence" / "search.packet-input.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_packet(replay_path: Path, evidence_path: Path) -> dict:
    replay = load_manual_replay_fixture(replay_path)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    return build_incident_packet_from_bundle(normalized, _load_json(evidence_path))


def test_load_investigator_routing_config_freezes_local_first_mode() -> None:
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    assert config.default_mode == "local_first"
    assert config.routing.require_needs_investigation is True
    assert config.routing.allowed_provider_order == ("local_primary",)
    assert config.routing.allow_cloud_fallback is True
    assert config.local_primary.enabled is True
    assert config.local_primary.model_provider == "local_vllm"
    assert config.local_primary.model_name == "local-primary-smoke"
    assert config.local_primary.budget.wall_time_seconds == 120
    assert config.local_primary.budget.max_tool_calls == 8
    assert config.local_primary.trigger_rules["novelty_at_or_above"] == 0.79
    assert config.local_primary.trigger_rules["severity_probability_at_or_above"] == 0.95
    assert config.local_primary.trigger_rules["blast_radius_at_or_above"] == 0.84
    assert config.local_primary.trigger_rules["page_owner_requires_confidence_below"] == 0.61
    assert config.cloud_fallback.enabled is True
    assert config.cloud_fallback.available_phase == "P5"
    assert config.cloud_fallback.model_provider == "openai"
    assert config.cloud_fallback.model_name == "cloud-fallback-smoke"
    assert config.cloud_fallback.budget.max_invocation_rate_total == 0.05
    assert config.cloud_fallback.budget.max_invocation_rate_investigated == 0.25
    assert config.cloud_fallback.budget.max_wall_time_seconds == 90
    assert config.cloud_fallback.budget.max_handoff_tokens == 1200
    assert config.cloud_fallback.audit.require_parent_investigation_id is True
    assert config.cloud_fallback.audit.require_handoff_markdown is True
    assert config.cloud_fallback.audit.require_handoff_tokens_estimate is True
    assert config.cloud_fallback.audit.require_failure_reason_note is True


def test_plan_investigation_routes_checkout_case_to_local_primary() -> None:
    packet = _build_packet(CHECKOUT_REPLAY, CHECKOUT_EVIDENCE)
    decision = resolve_runtime_scorer(
        repo_root=REPO_ROOT,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    ).score_packet(packet, retrieval_hits=_load_json(CHECKOUT_DECISION)["retrieval_hits"])
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)

    assert decision["analyzer_version"] == "trained-scorer-2026-04-19"

    assert plan.should_investigate is True
    assert plan.selected_provider == "local_primary"
    assert plan.provider_order == ("local_primary",)
    assert plan.allow_cloud_fallback is True
    assert plan.budget is not None
    assert plan.budget.wall_time_seconds == 120
    assert plan.request is not None
    assert plan.request.retrieval_packet_ids == ("ipk_checkout_post_pay_20260411t110000z",)
    assert set(plan.trigger_reasons) == {
        "calibrated_severity_high_route_gate",
    }


def test_plan_investigation_skips_non_triggered_cases() -> None:
    packet = _build_packet(CATALOG_REPLAY, CATALOG_EVIDENCE)
    decision = resolve_runtime_scorer(
        repo_root=REPO_ROOT,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    ).score_packet(
        packet,
        retrieval_hits=[
            {
                "packet_id": "ipk_catalog_get_items_20260410t090000z",
                "similarity": 0.77,
                "known_outcome": "benign",
            }
        ],
    )
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)

    assert plan.should_investigate is False
    assert plan.selected_provider is None
    assert plan.budget is None
    assert plan.request is None


def test_plan_investigation_skips_search_case_after_routing_recovery_retune() -> None:
    packet = _build_packet(SEARCH_REPLAY, SEARCH_EVIDENCE)
    decision = resolve_runtime_scorer(
        repo_root=REPO_ROOT,
        thresholds=load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml"),
    ).score_packet(
        packet,
        retrieval_hits=[
            {
                "packet_id": "ipk_search_get_api_query_20260416t141008z",
                "similarity": 0.78,
                "known_outcome": "severe",
            }
        ],
    )
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    plan = plan_investigation(packet, decision, config=config)

    assert decision["analyzer_version"] == "trained-scorer-2026-04-19"
    assert decision["needs_investigation"] is True
    assert plan.should_investigate is False
    assert plan.selected_provider is None
    assert plan.budget is None
    assert plan.request is None


def test_build_investigation_request_caps_reference_lists_to_budget() -> None:
    packet = _build_packet(CHECKOUT_REPLAY, CHECKOUT_EVIDENCE)
    decision = _load_json(CHECKOUT_DECISION)
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    packet_with_many_refs = copy.deepcopy(packet)
    packet_with_many_refs["evidence_refs"]["prometheus_query_refs"] = [f"prom://query/{index}" for index in range(12)]
    packet_with_many_refs["evidence_refs"]["signoz_query_refs"] = [f"signoz://query/{index}" for index in range(12)]
    packet_with_many_refs["signoz"]["sample_trace_ids"] = [f"trace-{index}" for index in range(12)]
    packet_with_many_refs["signoz"]["sample_log_refs"] = [f"signoz://logs/row-{index}" for index in range(12)]

    decision_with_many_hits = copy.deepcopy(decision)
    decision_with_many_hits["retrieval_hits"] = [
        {
            "packet_id": f"ipk_checkout_reference_{index}",
            "similarity": 0.82,
            "known_outcome": "severe",
        }
        for index in range(12)
    ]

    request = build_investigation_request(
        packet_with_many_refs,
        decision_with_many_hits,
        budget=config.local_primary.budget,
        code_search_refs=tuple(f"repo://checkout/path/{index}" for index in range(12)),
    )

    assert len(request.retrieval_packet_ids) == config.local_primary.budget.max_retrieval_refs
    assert len(request.prometheus_query_refs) == config.local_primary.budget.max_tool_calls
    assert len(request.signoz_query_refs) == config.local_primary.budget.max_tool_calls
    assert len(request.sample_trace_ids) == config.local_primary.budget.max_trace_refs
    assert len(request.sample_log_refs) == config.local_primary.budget.max_log_refs
    assert len(request.code_search_refs) == config.local_primary.budget.max_code_refs
