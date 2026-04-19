"""Benchmark harness for cloud-fallback closeout evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from jsonschema import Draft202012Validator

from app.analyzer.base import AnalyzerThresholds, load_thresholds
from app.analyzer.calibrate import ACCEPTED_CALIBRATION_LABELS, ACCEPTED_RETRIEVAL_OUTCOMES
from app.analyzer.contracts import RetrievalHit
from app.analyzer.runtime import resolve_runtime_scorer
from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.router import InvestigatorRoutingConfig, load_investigator_routing_config
from app.investigator.runtime import run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.reports.markdown_builder import render_alert_report

CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION: Final = "cloud-fallback-routing-eval-corpus.v1"
LOCAL_PRIMARY_ROUTING_EVAL_CORPUS_SCHEMA_VERSION: Final = "local-primary-routing-eval-corpus.v1"
CLOUD_BENCHMARK_SUMMARY_VERSION: Final = "cloud-fallback-benchmark-summary.v1"
FINAL_INVESTIGATION_SCHEMA_VALIDITY_REQUIRED: Final = 1.0
CLOUD_UNAVAILABLE_FALLBACK_REPORT_SUCCESS_REQUIRED: Final = 0.95


class CloudBenchmarkCase(TypedDict):
    case_id: str
    label: str
    expected_needs_investigation: bool
    expected_local_primary_invocation: bool
    expected_cloud_fallback_invocation: bool
    replay_fixture: str
    evidence_fixture: str
    retrieval_hits: list[RetrievalHit]


class CloudBenchmarkCorpusContract(TypedDict):
    schema_version: str
    total_cases: int
    expected_cloud_fallback_case_count: int
    minimum_cases: int
    measurement_ready: bool
    blocking_reasons: list[str]


class AcceptanceCheck(TypedDict):
    actual: float | bool
    expected: float | bool
    comparator: str
    passed: bool


class BenchmarkAcceptance(TypedDict):
    accepted: bool
    blockers: list[str]
    checks: dict[str, AcceptanceCheck]


class CloudRoutingSnapshot(TypedDict):
    allow_cloud_fallback: bool
    cloud_fallback_enabled: bool
    local_confidence_below: float
    unresolved_unknowns_required: bool
    conflicting_hypotheses_required: bool
    max_invocation_rate_total: float
    max_invocation_rate_investigated: float
    max_wall_time_seconds: int
    max_handoff_tokens: int


class CloudBenchmarkGateSnapshot(TypedDict):
    required_corpus_schema_version: str
    minimum_cases: int
    cloud_fallback_rate_total_max: float
    cloud_fallback_rate_investigated_max: float
    cloud_fallback_p95_wall_time_sec_max: int
    compressed_handoff_p95_tokens_max: int
    final_investigation_schema_validity_required: float
    cloud_unavailable_fallback_report_success_required: float


class CloudBenchmarkSummary(TypedDict):
    summary_version: str
    generated_at: str
    corpus_path: str
    corpus_contract: CloudBenchmarkCorpusContract
    routing_snapshot: CloudRoutingSnapshot
    gate_snapshot: CloudBenchmarkGateSnapshot
    metrics: dict[str, float | int]
    acceptance: BenchmarkAcceptance
    accepted_cloud_fallback_baseline: bool
    notes: list[str]


class _CrashingLocalPrimaryProvider:
    def investigate(self, request: object) -> object:
        raise RuntimeError("local tool budget exhausted before follow-up completed")


class _CrashingCloudProvider:
    def investigate(self, request: object) -> object:
        raise RuntimeError("vendor timeout during bounded cloud review")


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_retrieval_hit(*, case_id: str, hit_index: int, payload: object) -> RetrievalHit:
    _require(isinstance(payload, dict), f"case {case_id} retrieval hit #{hit_index} must be an object")

    packet_id = str(payload.get("packet_id") or "").strip()
    similarity = payload.get("similarity")
    known_outcome = str(payload.get("known_outcome") or "").strip()

    _require(packet_id != "", f"case {case_id} retrieval hit #{hit_index} missing packet_id")
    _require(isinstance(similarity, (int, float)), f"case {case_id} retrieval hit #{hit_index} missing similarity")
    _require(
        known_outcome in ACCEPTED_RETRIEVAL_OUTCOMES,
        f"case {case_id} retrieval hit #{hit_index} unsupported known_outcome '{known_outcome}'",
    )

    return {
        "packet_id": packet_id,
        "similarity": float(similarity),
        "known_outcome": known_outcome,
    }


def _validate_case(
    *,
    case_index: int,
    payload: object,
    schema_version: str,
    seen_case_ids: set[str],
) -> CloudBenchmarkCase:
    _require(isinstance(payload, dict), f"benchmark case #{case_index} must be an object")

    case_id = str(payload.get("case_id") or "").strip()
    label = str(payload.get("label") or "").strip()
    expected_needs_investigation = payload.get("expected_needs_investigation")
    expected_local_primary_invocation = payload.get("expected_local_primary_invocation")
    expected_cloud_fallback_invocation = payload.get("expected_cloud_fallback_invocation")
    replay_fixture = str(payload.get("replay_fixture") or "").strip()
    evidence_fixture = str(payload.get("evidence_fixture") or "").strip()
    retrieval_hits_payload = payload.get("retrieval_hits")

    _require(case_id != "", f"benchmark case #{case_index} missing case_id")
    _require(case_id not in seen_case_ids, f"duplicate benchmark case_id '{case_id}'")
    _require(label in ACCEPTED_CALIBRATION_LABELS, f"case {case_id} has unsupported label '{label}'")
    _require(isinstance(expected_needs_investigation, bool), f"case {case_id} expected_needs_investigation must be a boolean")
    _require(
        isinstance(expected_local_primary_invocation, bool),
        f"case {case_id} expected_local_primary_invocation must be a boolean",
    )
    if schema_version == CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION:
        _require(
            isinstance(expected_cloud_fallback_invocation, bool),
            f"case {case_id} expected_cloud_fallback_invocation must be a boolean in cloud routing corpus",
        )
    else:
        expected_cloud_fallback_invocation = False
    _require(replay_fixture != "", f"case {case_id} missing replay_fixture")
    _require(evidence_fixture != "", f"case {case_id} missing evidence_fixture")
    _require(isinstance(retrieval_hits_payload, list), f"case {case_id} retrieval_hits must be a list")

    retrieval_hits = [
        _validate_retrieval_hit(case_id=case_id, hit_index=hit_index, payload=hit)
        for hit_index, hit in enumerate(retrieval_hits_payload)
    ]
    seen_case_ids.add(case_id)

    return {
        "case_id": case_id,
        "label": label,
        "expected_needs_investigation": bool(expected_needs_investigation),
        "expected_local_primary_invocation": bool(expected_local_primary_invocation),
        "expected_cloud_fallback_invocation": bool(expected_cloud_fallback_invocation),
        "replay_fixture": replay_fixture,
        "evidence_fixture": evidence_fixture,
        "retrieval_hits": retrieval_hits,
    }


def load_cloud_fallback_benchmark_corpus(path: str | Path) -> tuple[str, list[CloudBenchmarkCase]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _require(isinstance(payload, dict), "cloud benchmark corpus payload must be an object")
    schema_version = str(payload.get("schema_version") or "")
    _require(
        schema_version in {LOCAL_PRIMARY_ROUTING_EVAL_CORPUS_SCHEMA_VERSION, CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION},
        f"unsupported cloud benchmark corpus schema_version '{schema_version}'",
    )
    cases_payload = payload.get("cases")
    _require(isinstance(cases_payload, list), "cloud benchmark corpus cases must be a list")

    seen_case_ids: set[str] = set()
    cases = [
        _validate_case(
            case_index=case_index,
            payload=case,
            schema_version=schema_version,
            seen_case_ids=seen_case_ids,
        )
        for case_index, case in enumerate(cases_payload)
    ]
    return schema_version, cases


def evaluate_cloud_benchmark_corpus_contract(
    schema_version: str,
    cases: list[CloudBenchmarkCase],
    *,
    thresholds: AnalyzerThresholds,
) -> CloudBenchmarkCorpusContract:
    total_cases = len(cases)
    expected_cloud_fallback_case_count = sum(int(case["expected_cloud_fallback_invocation"]) for case in cases)
    blocking_reasons: list[str] = []
    if schema_version != CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION:
        blocking_reasons.append("dedicated_cloud_routing_eval_corpus_missing")
    if total_cases < thresholds.minimum_calibration_cases:
        blocking_reasons.append("total_cases_below_minimum")

    return {
        "schema_version": schema_version,
        "total_cases": total_cases,
        "expected_cloud_fallback_case_count": expected_cloud_fallback_case_count,
        "minimum_cases": thresholds.minimum_calibration_cases,
        "measurement_ready": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
    }


def cloud_routing_snapshot(config: InvestigatorRoutingConfig) -> CloudRoutingSnapshot:
    rules = config.cloud_fallback.trigger_rules
    budget = config.cloud_fallback.budget
    return {
        "allow_cloud_fallback": config.routing.allow_cloud_fallback,
        "cloud_fallback_enabled": config.cloud_fallback.enabled,
        "local_confidence_below": float(rules["local_confidence_below"]),
        "unresolved_unknowns_required": bool(rules["unresolved_unknowns_required"]),
        "conflicting_hypotheses_required": bool(rules["conflicting_hypotheses_required"]),
        "max_invocation_rate_total": budget.max_invocation_rate_total,
        "max_invocation_rate_investigated": budget.max_invocation_rate_investigated,
        "max_wall_time_seconds": budget.max_wall_time_seconds,
        "max_handoff_tokens": budget.max_handoff_tokens,
    }


def cloud_benchmark_gate_snapshot(config: InvestigatorRoutingConfig) -> CloudBenchmarkGateSnapshot:
    budget = config.cloud_fallback.budget
    return {
        "required_corpus_schema_version": CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
        "minimum_cases": 10,
        "cloud_fallback_rate_total_max": budget.max_invocation_rate_total,
        "cloud_fallback_rate_investigated_max": budget.max_invocation_rate_investigated,
        "cloud_fallback_p95_wall_time_sec_max": budget.max_wall_time_seconds,
        "compressed_handoff_p95_tokens_max": budget.max_handoff_tokens,
        "final_investigation_schema_validity_required": FINAL_INVESTIGATION_SCHEMA_VALIDITY_REQUIRED,
        "cloud_unavailable_fallback_report_success_required": CLOUD_UNAVAILABLE_FALLBACK_REPORT_SUCCESS_REQUIRED,
    }


def _check(*, actual: float | bool, expected: float | bool, comparator: str, passed: bool) -> AcceptanceCheck:
    return {
        "actual": actual,
        "expected": expected,
        "comparator": comparator,
        "passed": passed,
    }


def evaluate_cloud_fallback_benchmark_acceptance(
    *,
    corpus_contract: CloudBenchmarkCorpusContract,
    metrics: dict[str, float | int],
    gate_snapshot: CloudBenchmarkGateSnapshot,
) -> BenchmarkAcceptance:
    measurement_ready = corpus_contract["measurement_ready"]
    total_rate = float(metrics["cloud_fallback_rate_total"])
    investigated_rate = float(metrics["cloud_fallback_rate_investigated"])
    wall_time = float(metrics["cloud_fallback_p95_wall_time_sec"])
    handoff_tokens = float(metrics["compressed_handoff_p95_tokens"])
    schema_validity = float(metrics["final_investigation_schema_validity_rate"])
    fallback_success = float(metrics["cloud_unavailable_fallback_report_success_rate"])

    checks = {
        "benchmark_measurement_ready": _check(
            actual=measurement_ready,
            expected=True,
            comparator="==",
            passed=measurement_ready is True,
        ),
        "cloud_fallback_rate_total": _check(
            actual=total_rate,
            expected=gate_snapshot["cloud_fallback_rate_total_max"],
            comparator="<=",
            passed=total_rate <= gate_snapshot["cloud_fallback_rate_total_max"],
        ),
        "cloud_fallback_rate_investigated": _check(
            actual=investigated_rate,
            expected=gate_snapshot["cloud_fallback_rate_investigated_max"],
            comparator="<=",
            passed=investigated_rate <= gate_snapshot["cloud_fallback_rate_investigated_max"],
        ),
        "cloud_fallback_p95_wall_time_sec": _check(
            actual=wall_time,
            expected=gate_snapshot["cloud_fallback_p95_wall_time_sec_max"],
            comparator="<=",
            passed=wall_time <= gate_snapshot["cloud_fallback_p95_wall_time_sec_max"],
        ),
        "compressed_handoff_p95_tokens": _check(
            actual=handoff_tokens,
            expected=gate_snapshot["compressed_handoff_p95_tokens_max"],
            comparator="<=",
            passed=handoff_tokens <= gate_snapshot["compressed_handoff_p95_tokens_max"],
        ),
        "final_investigation_schema_validity_rate": _check(
            actual=schema_validity,
            expected=gate_snapshot["final_investigation_schema_validity_required"],
            comparator="==",
            passed=schema_validity == gate_snapshot["final_investigation_schema_validity_required"],
        ),
        "cloud_unavailable_fallback_report_success_rate": _check(
            actual=fallback_success,
            expected=gate_snapshot["cloud_unavailable_fallback_report_success_required"],
            comparator=">=",
            passed=fallback_success >= gate_snapshot["cloud_unavailable_fallback_report_success_required"],
        ),
    }

    blockers: list[str] = []
    if not checks["benchmark_measurement_ready"]["passed"]:
        blockers.append("benchmark_measurement_not_ready")
    if not checks["cloud_fallback_rate_total"]["passed"]:
        blockers.append("cloud_fallback_rate_total_above_gate")
    if not checks["cloud_fallback_rate_investigated"]["passed"]:
        blockers.append("cloud_fallback_rate_investigated_above_gate")
    if not checks["cloud_fallback_p95_wall_time_sec"]["passed"]:
        blockers.append("cloud_fallback_wall_time_above_gate")
    if not checks["compressed_handoff_p95_tokens"]["passed"]:
        blockers.append("compressed_handoff_tokens_above_gate")
    if not checks["final_investigation_schema_validity_rate"]["passed"]:
        blockers.append("final_investigation_schema_invalid")
    if not checks["cloud_unavailable_fallback_report_success_rate"]["passed"]:
        blockers.append("cloud_unavailable_fallback_report_success_below_gate")

    return {
        "accepted": not blockers,
        "blockers": blockers,
        "checks": checks,
    }


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _p95(values: list[float | int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, (len(ordered) * 95 + 99) // 100 - 1)
    return ordered[index]


def _failure_smoke_success(*, repo_root: Path) -> bool:
    packet = build_incident_packet_from_bundle(
        normalize_alertmanager_payload(
            load_manual_replay_fixture(repo_root / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json")[
                "alert_payload"
            ],
            candidate_source="manual_replay",
        ),
        _load_json(repo_root / "fixtures" / "evidence" / "checkout.packet-input.json"),
    )
    decision = _load_json(repo_root / "fixtures" / "evidence" / "checkout.local-decision.json")
    execution = run_investigation_runtime(
        packet,
        decision,
        config_path=repo_root / "configs" / "escalation.yaml",
        local_provider=_CrashingLocalPrimaryProvider(),
        cloud_provider=_CrashingCloudProvider(),
    )
    if execution.final_result is None:
        return False
    report = render_alert_report(packet, decision, execution.final_result)
    return (
        execution.cloud_audit is not None
        and execution.cloud_audit.fallback_used is True
        and execution.final_result["investigator_tier"] == "local_primary_investigator"
        and "investigation_stage: local_primary" in report
    )


def run_cloud_fallback_benchmark(
    *,
    corpus_path: str | Path,
    output_path: str | Path,
    repo_root: str | Path = Path("."),
) -> CloudBenchmarkSummary:
    repo_root = Path(repo_root)
    corpus_path = Path(corpus_path)
    output_path = Path(output_path)

    thresholds = load_thresholds(repo_root / "configs" / "thresholds.yaml")
    scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=thresholds)
    config = load_investigator_routing_config(repo_root / "configs" / "escalation.yaml")
    validator = Draft202012Validator(load_investigation_schema())

    schema_version, cases = load_cloud_fallback_benchmark_corpus(corpus_path)
    corpus_contract = evaluate_cloud_benchmark_corpus_contract(schema_version, cases, thresholds=thresholds)
    gate_snapshot = cloud_benchmark_gate_snapshot(config)

    investigated_case_count = 0
    actual_cloud_fallback_invocation_count = 0
    final_schema_valid_count = 0
    cloud_wall_times: list[float] = []
    handoff_tokens: list[int] = []
    routing_alignment_count = 0

    for case in cases:
        replay = load_manual_replay_fixture(repo_root / case["replay_fixture"])
        normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
        evidence = _load_json(repo_root / case["evidence_fixture"])
        packet = build_incident_packet_from_bundle(normalized, evidence)
        decision = scorer.score_packet(packet, retrieval_hits=case["retrieval_hits"])
        execution = run_investigation_runtime(
            packet,
            decision,
            config_path=repo_root / "configs" / "escalation.yaml",
        )

        used_cloud_fallback = bool(
            execution.final_result is not None
            and execution.final_result["investigator_tier"] == "cloud_fallback_investigator"
        )
        if used_cloud_fallback == case["expected_cloud_fallback_invocation"]:
            routing_alignment_count += 1

        if execution.route_plan.should_investigate:
            investigated_case_count += 1
            if execution.final_result is not None:
                errors = sorted(validator.iter_errors(execution.final_result), key=lambda error: error.json_path)
                if not errors:
                    final_schema_valid_count += 1

        if used_cloud_fallback:
            actual_cloud_fallback_invocation_count += 1
            if execution.cloud_audit is not None:
                cloud_wall_times.append(execution.cloud_audit.wall_time_seconds)
            if execution.final_result is not None:
                compressed_handoff = execution.final_result.get("compressed_handoff") or {}
                handoff_tokens.append(int(compressed_handoff.get("handoff_tokens_estimate") or 0))

    failure_smoke_success = _failure_smoke_success(repo_root=repo_root)
    fallback_success_rate = 1.0 if failure_smoke_success else 0.0
    final_schema_validity_rate = (
        final_schema_valid_count / investigated_case_count if investigated_case_count else 1.0
    )
    cloud_fallback_rate_total = actual_cloud_fallback_invocation_count / len(cases) if cases else 0.0
    cloud_fallback_rate_investigated = (
        actual_cloud_fallback_invocation_count / investigated_case_count if investigated_case_count else 0.0
    )
    routing_alignment_rate = routing_alignment_count / len(cases) if cases else 1.0

    metrics = {
        "total_cases": len(cases),
        "expected_cloud_fallback_case_count": corpus_contract["expected_cloud_fallback_case_count"],
        "investigated_case_count": investigated_case_count,
        "actual_cloud_fallback_invocation_count": actual_cloud_fallback_invocation_count,
        "cloud_fallback_rate_total": round(cloud_fallback_rate_total, 4),
        "cloud_fallback_rate_investigated": round(cloud_fallback_rate_investigated, 4),
        "cloud_routing_label_alignment_rate": round(routing_alignment_rate, 4),
        "cloud_fallback_p95_wall_time_sec": round(_p95(cloud_wall_times), 4),
        "compressed_handoff_p95_tokens": round(_p95(handoff_tokens), 4),
        "final_investigation_schema_validity_rate": round(final_schema_validity_rate, 4),
        "cloud_unavailable_fallback_report_success_rate": round(fallback_success_rate, 4),
    }
    acceptance = evaluate_cloud_fallback_benchmark_acceptance(
        corpus_contract=corpus_contract,
        metrics=metrics,
        gate_snapshot=gate_snapshot,
    )

    notes: list[str] = []
    if actual_cloud_fallback_invocation_count == 0:
        notes.append(
            "cloud benchmark corpus produced zero runtime cloud invocations; cloud path correctness is separately proven by targeted runtime/failure smoke tests"
        )

    summary: CloudBenchmarkSummary = {
        "summary_version": CLOUD_BENCHMARK_SUMMARY_VERSION,
        "generated_at": _utc_now(),
        "corpus_path": str(corpus_path.resolve()),
        "corpus_contract": corpus_contract,
        "routing_snapshot": cloud_routing_snapshot(config),
        "gate_snapshot": gate_snapshot,
        "metrics": metrics,
        "acceptance": acceptance,
        "accepted_cloud_fallback_baseline": acceptance["accepted"],
        "notes": notes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
