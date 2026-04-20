"""Benchmark harness for local-primary investigator closeout evidence."""

from __future__ import annotations

import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from jsonschema import Draft202012Validator

from app.analyzer.base import AnalyzerThresholds, load_thresholds
from app.analyzer.calibrate import (
    ACCEPTED_CALIBRATION_LABELS,
    ACCEPTED_RETRIEVAL_OUTCOMES,
    CALIBRATION_CORPUS_SCHEMA_VERSION,
)
from app.analyzer.contracts import RetrievalHit
from app.analyzer.runtime import resolve_runtime_scorer
from app.investigator.contracts import load_schema as load_investigation_schema
from app.investigator.fallback import run_local_primary_with_fallback
from app.investigator.local_primary import LocalPrimaryInvestigator, LocalPrimaryResidentLifecycle
from app.investigator.router import InvestigatorRoutingConfig, load_investigator_routing_config, plan_investigation
from app.investigator.runtime import LocalPrimaryRecoveryRequired, run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture

ROUTING_EVAL_CORPUS_SCHEMA_VERSION: Final = "local-primary-routing-eval-corpus.v1"
BENCHMARK_SUMMARY_VERSION: Final = "local-primary-benchmark-summary.v1"
LOCAL_PRIMARY_INVOCATION_RATE_MAX: Final = 0.20
MINIMUM_ROUTING_EVAL_INVESTIGATION_CASES: Final = 2
STRUCTURED_COMPLETENESS_MIN: Final = 0.95
DEGRADED_FALLBACK_VALIDITY_REQUIRED: Final = 1.0
DIRECT_RUNTIME_ABNORMAL_FALLBACK_VALIDITY_REQUIRED: Final = 1.0
WARNING_WORKER_RECOVERY_WAIT_VALIDITY_REQUIRED: Final = 1.0


class BenchmarkCase(TypedDict):
    case_id: str
    label: str
    expected_needs_investigation: bool
    expected_local_primary_invocation: bool
    replay_fixture: str
    evidence_fixture: str
    retrieval_hits: list[RetrievalHit]


class BenchmarkCorpusContract(TypedDict):
    schema_version: str
    total_cases: int
    expected_investigation_case_count: int
    minimum_cases: int
    minimum_investigation_cases: int
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


class RoutingSnapshot(TypedDict):
    default_mode: str
    require_needs_investigation: bool
    allowed_provider_order: list[str]
    allow_cloud_fallback: bool
    local_primary_model_provider: str
    local_primary_model_name: str
    local_primary_budget: dict[str, int]


class BenchmarkGateSnapshot(TypedDict):
    required_corpus_schema_version: str
    minimum_cases: int
    minimum_investigation_cases: int
    local_primary_invocation_rate_max: float
    local_primary_p95_wall_time_sec_max: int
    average_tool_calls_per_investigation_max: int
    structured_completeness_min: float
    degraded_fallback_validity_required: float
    direct_runtime_abnormal_fallback_validity_required: float
    warning_worker_recovery_wait_validity_required: float


class BenchmarkSummary(TypedDict):
    summary_version: str
    generated_at: str
    corpus_path: str
    corpus_contract: BenchmarkCorpusContract
    routing_snapshot: RoutingSnapshot
    gate_snapshot: BenchmarkGateSnapshot
    metrics: dict[str, float | int]
    acceptance: BenchmarkAcceptance
    accepted_local_primary_baseline: bool
    notes: list[str]


class _CrashingBenchmarkProvider:
    def investigate(self, request: object) -> object:
        raise RuntimeError("benchmark-injected local-primary failure")


class _DegradedResidentBenchmarkProvider:
    resident_lifecycle = LocalPrimaryResidentLifecycle(
        service_mode="resident_prewarm_on_boot",
        invocation_scope="needs_investigation_only",
        startup_cost_policy="excluded_from_per_warning_budget",
        provider_mode="real_adapter_resident",
        state="degraded",
        gate_state="ready",
        model_name="gemma4-26b",
        prewarm_completed_once=True,
        prewarm_attempt_count=1,
        prewarm_source="provider_init",
        reason="local_primary resident prewarm failed: benchmark injected resident outage",
    )

    def investigate(self, request: object) -> object:
        raise AssertionError("degraded resident benchmark provider should not be invoked directly")


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


def _validate_benchmark_case(
    *,
    case_index: int,
    payload: object,
    schema_version: str,
    seen_case_ids: set[str],
) -> BenchmarkCase:
    _require(isinstance(payload, dict), f"benchmark case #{case_index} must be an object")

    case_id = str(payload.get("case_id") or "").strip()
    label = str(payload.get("label") or "").strip()
    expected_needs_investigation = payload.get("expected_needs_investigation")
    expected_local_primary_invocation = payload.get("expected_local_primary_invocation")
    replay_fixture = str(payload.get("replay_fixture") or "").strip()
    evidence_fixture = str(payload.get("evidence_fixture") or "").strip()
    retrieval_hits_payload = payload.get("retrieval_hits")

    _require(case_id != "", f"benchmark case #{case_index} missing case_id")
    _require(case_id not in seen_case_ids, f"duplicate benchmark case_id '{case_id}'")
    _require(label in ACCEPTED_CALIBRATION_LABELS, f"case {case_id} has unsupported label '{label}'")
    _require(
        isinstance(expected_needs_investigation, bool),
        f"case {case_id} expected_needs_investigation must be a boolean",
    )
    if schema_version == ROUTING_EVAL_CORPUS_SCHEMA_VERSION:
        _require(
            isinstance(expected_local_primary_invocation, bool),
            f"case {case_id} expected_local_primary_invocation must be a boolean in routing-eval corpus",
        )
    else:
        expected_local_primary_invocation = expected_needs_investigation
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
        "expected_needs_investigation": expected_needs_investigation,
        "expected_local_primary_invocation": bool(expected_local_primary_invocation),
        "replay_fixture": replay_fixture,
        "evidence_fixture": evidence_fixture,
        "retrieval_hits": retrieval_hits,
    }


def load_local_primary_benchmark_corpus(path: str | Path) -> tuple[str, list[BenchmarkCase]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _require(isinstance(payload, dict), "benchmark corpus payload must be an object")
    schema_version = payload.get("schema_version")
    _require(
        schema_version in {CALIBRATION_CORPUS_SCHEMA_VERSION, ROUTING_EVAL_CORPUS_SCHEMA_VERSION},
        f"unsupported benchmark corpus schema_version '{schema_version}'",
    )
    cases_payload = payload.get("cases")
    _require(isinstance(cases_payload, list), "benchmark corpus cases must be a list")

    seen_case_ids: set[str] = set()
    cases = [
        _validate_benchmark_case(
            case_index=case_index,
            payload=case,
            schema_version=str(schema_version),
            seen_case_ids=seen_case_ids,
        )
        for case_index, case in enumerate(cases_payload)
    ]
    return str(schema_version), cases


def evaluate_benchmark_corpus_contract(
    schema_version: str,
    cases: list[BenchmarkCase],
    *,
    thresholds: AnalyzerThresholds,
) -> BenchmarkCorpusContract:
    total_cases = len(cases)
    expected_investigation_case_count = sum(int(case["expected_local_primary_invocation"]) for case in cases)
    minimum_investigation_cases = MINIMUM_ROUTING_EVAL_INVESTIGATION_CASES
    blocking_reasons: list[str] = []
    if schema_version != ROUTING_EVAL_CORPUS_SCHEMA_VERSION:
        blocking_reasons.append("dedicated_routing_eval_corpus_missing")
    if total_cases < thresholds.minimum_calibration_cases:
        blocking_reasons.append("total_cases_below_minimum")
    if expected_investigation_case_count < minimum_investigation_cases:
        blocking_reasons.append("expected_investigation_cases_below_minimum")

    return {
        "schema_version": schema_version,
        "total_cases": total_cases,
        "expected_investigation_case_count": expected_investigation_case_count,
        "minimum_cases": thresholds.minimum_calibration_cases,
        "minimum_investigation_cases": minimum_investigation_cases,
        "measurement_ready": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
    }


def routing_snapshot(config: InvestigatorRoutingConfig) -> RoutingSnapshot:
    budget = config.local_primary.budget
    return {
        "default_mode": config.default_mode,
        "require_needs_investigation": config.routing.require_needs_investigation,
        "allowed_provider_order": list(config.routing.allowed_provider_order),
        "allow_cloud_fallback": config.routing.allow_cloud_fallback,
        "local_primary_model_provider": config.local_primary.model_provider,
        "local_primary_model_name": config.local_primary.model_name,
        "local_primary_budget": {
            "wall_time_seconds": budget.wall_time_seconds,
            "max_tool_calls": budget.max_tool_calls,
            "max_prompt_tokens": budget.max_prompt_tokens,
            "max_completion_tokens": budget.max_completion_tokens,
            "max_retrieval_refs": budget.max_retrieval_refs,
            "max_trace_refs": budget.max_trace_refs,
            "max_log_refs": budget.max_log_refs,
            "max_code_refs": budget.max_code_refs,
        },
    }


def benchmark_gate_snapshot(thresholds: AnalyzerThresholds, config: InvestigatorRoutingConfig) -> BenchmarkGateSnapshot:
    return {
        "required_corpus_schema_version": ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
        "minimum_cases": thresholds.minimum_calibration_cases,
        "minimum_investigation_cases": MINIMUM_ROUTING_EVAL_INVESTIGATION_CASES,
        "local_primary_invocation_rate_max": LOCAL_PRIMARY_INVOCATION_RATE_MAX,
        "local_primary_p95_wall_time_sec_max": config.local_primary.budget.wall_time_seconds,
        "average_tool_calls_per_investigation_max": config.local_primary.budget.max_tool_calls,
        "structured_completeness_min": STRUCTURED_COMPLETENESS_MIN,
        "degraded_fallback_validity_required": DEGRADED_FALLBACK_VALIDITY_REQUIRED,
        "direct_runtime_abnormal_fallback_validity_required": DIRECT_RUNTIME_ABNORMAL_FALLBACK_VALIDITY_REQUIRED,
        "warning_worker_recovery_wait_validity_required": WARNING_WORKER_RECOVERY_WAIT_VALIDITY_REQUIRED,
    }


def _metric_check(*, actual: float | bool, expected: float | bool, comparator: str, passed: bool) -> AcceptanceCheck:
    return {
        "actual": actual,
        "expected": expected,
        "comparator": comparator,
        "passed": passed,
    }


def evaluate_local_primary_acceptance(
    *,
    corpus_contract: BenchmarkCorpusContract,
    metrics: dict[str, float | int],
    gate_snapshot: BenchmarkGateSnapshot,
) -> BenchmarkAcceptance:
    invocation_rate = float(metrics["local_primary_invocation_rate"])
    p95_wall_time = float(metrics["local_primary_p95_wall_time_sec"])
    average_tool_calls = float(metrics["average_tool_calls_per_investigation"])
    completeness = float(metrics["structured_completeness_rate"])
    degraded_validity = float(metrics["degraded_fallback_validity_rate"])
    direct_runtime_abnormal_validity = float(metrics["direct_runtime_abnormal_fallback_validity_rate"])
    warning_worker_recovery_wait_validity = float(metrics["warning_worker_recovery_wait_validity_rate"])

    checks: dict[str, AcceptanceCheck] = {
        "benchmark_measurement_ready": _metric_check(
            actual=corpus_contract["measurement_ready"],
            expected=True,
            comparator="==",
            passed=corpus_contract["measurement_ready"],
        ),
        "local_primary_invocation_rate": _metric_check(
            actual=invocation_rate,
            expected=gate_snapshot["local_primary_invocation_rate_max"],
            comparator="<=",
            passed=invocation_rate <= gate_snapshot["local_primary_invocation_rate_max"],
        ),
        "local_primary_p95_wall_time_sec": _metric_check(
            actual=p95_wall_time,
            expected=gate_snapshot["local_primary_p95_wall_time_sec_max"],
            comparator="<=",
            passed=p95_wall_time <= gate_snapshot["local_primary_p95_wall_time_sec_max"],
        ),
        "average_tool_calls_per_investigation": _metric_check(
            actual=average_tool_calls,
            expected=gate_snapshot["average_tool_calls_per_investigation_max"],
            comparator="<=",
            passed=average_tool_calls <= gate_snapshot["average_tool_calls_per_investigation_max"],
        ),
        "structured_completeness_rate": _metric_check(
            actual=completeness,
            expected=gate_snapshot["structured_completeness_min"],
            comparator=">=",
            passed=completeness >= gate_snapshot["structured_completeness_min"],
        ),
        "degraded_fallback_validity_rate": _metric_check(
            actual=degraded_validity,
            expected=gate_snapshot["degraded_fallback_validity_required"],
            comparator="==",
            passed=degraded_validity == gate_snapshot["degraded_fallback_validity_required"],
        ),
        "direct_runtime_abnormal_fallback_validity_rate": _metric_check(
            actual=direct_runtime_abnormal_validity,
            expected=gate_snapshot["direct_runtime_abnormal_fallback_validity_required"],
            comparator="==",
            passed=direct_runtime_abnormal_validity == gate_snapshot["direct_runtime_abnormal_fallback_validity_required"],
        ),
        "warning_worker_recovery_wait_validity_rate": _metric_check(
            actual=warning_worker_recovery_wait_validity,
            expected=gate_snapshot["warning_worker_recovery_wait_validity_required"],
            comparator="==",
            passed=(
                warning_worker_recovery_wait_validity
                == gate_snapshot["warning_worker_recovery_wait_validity_required"]
            ),
        ),
    }

    blockers: list[str] = []
    if not checks["benchmark_measurement_ready"]["passed"]:
        blockers.append("benchmark_measurement_not_ready")
    if not checks["local_primary_invocation_rate"]["passed"]:
        blockers.append("local_primary_invocation_rate_above_gate")
    if not checks["local_primary_p95_wall_time_sec"]["passed"]:
        blockers.append("local_primary_p95_wall_time_above_gate")
    if not checks["average_tool_calls_per_investigation"]["passed"]:
        blockers.append("average_tool_calls_above_gate")
    if not checks["structured_completeness_rate"]["passed"]:
        blockers.append("structured_completeness_below_gate")
    if not checks["degraded_fallback_validity_rate"]["passed"]:
        blockers.append("degraded_fallback_invalid")
    if not checks["direct_runtime_abnormal_fallback_validity_rate"]["passed"]:
        blockers.append("direct_runtime_abnormal_fallback_invalid")
    if not checks["warning_worker_recovery_wait_validity_rate"]["passed"]:
        blockers.append("warning_worker_recovery_wait_invalid")

    return {
        "accepted": not blockers,
        "blockers": blockers,
        "checks": checks,
    }


def _extract_tool_calls_used(result: dict[str, object]) -> int:
    notes = result.get("analysis_updates", {}).get("notes", [])
    for note in notes:
        if isinstance(note, str) and note.startswith("tool_calls_used="):
            _, _, raw_value = note.partition("=")
            return int(raw_value)
    return 0


def _is_structured_complete(result: dict[str, object]) -> bool:
    summary = result["summary"]
    routing = result["routing"]
    evidence_refs = result["evidence_refs"]
    return all(
        [
            bool(summary["suspected_primary_cause"]),
            bool(summary["failure_chain_summary"]),
            bool(summary["reason_codes"]),
            bool(routing["repo_candidates"]),
            bool(evidence_refs["prometheus_ref_ids"]),
            bool(evidence_refs["signoz_ref_ids"]),
            bool(result["unknowns"]),
        ]
    )


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def run_local_primary_benchmark(
    *,
    corpus_path: str | Path,
    output_path: str | Path,
    repo_root: Path = Path('.'),
) -> BenchmarkSummary:
    thresholds = load_thresholds(repo_root / 'configs/thresholds.yaml')
    config = load_investigator_routing_config(repo_root / 'configs/escalation.yaml')
    scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=thresholds)
    provider = LocalPrimaryInvestigator.from_config(
        repo_root / 'configs/escalation.yaml',
        repo_root=repo_root,
    )
    validator = Draft202012Validator(load_investigation_schema())

    schema_version, corpus = load_local_primary_benchmark_corpus(corpus_path)
    corpus_contract = evaluate_benchmark_corpus_contract(schema_version, corpus, thresholds=thresholds)

    invocation_count = 0
    wall_times: list[float] = []
    tool_calls_total = 0
    structured_complete_count = 0
    degraded_fallback_valid_count = 0
    degraded_fallback_case_count = 0
    direct_runtime_abnormal_fallback_valid_count = 0
    direct_runtime_abnormal_fallback_case_count = 0
    warning_worker_recovery_wait_valid_count = 0
    warning_worker_recovery_wait_case_count = 0
    routing_label_match_count = 0

    for case in corpus:
        replay = load_manual_replay_fixture(repo_root / case["replay_fixture"])
        with (repo_root / case["evidence_fixture"]).open("r", encoding="utf-8") as handle:
            evidence_bundle = json.load(handle)
        packet = build_incident_packet_from_bundle(
            normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay"),
            evidence_bundle,
        )
        decision = scorer.score_packet(packet, retrieval_hits=case["retrieval_hits"])
        plan = plan_investigation(packet, decision, config=config)
        routing_label_match_count += int(plan.should_investigate == case["expected_local_primary_invocation"])
        if not plan.should_investigate or plan.request is None:
            continue

        invocation_count += 1
        started_at = time.perf_counter()
        result = run_local_primary_with_fallback(packet, decision, plan.request, provider=provider)
        wall_times.append(time.perf_counter() - started_at)
        tool_calls_total += _extract_tool_calls_used(result)

        errors = sorted(validator.iter_errors(result), key=lambda error: error.json_path)
        structured_complete_count += int(not errors and _is_structured_complete(result))

        degraded_result = run_local_primary_with_fallback(
            packet,
            decision,
            plan.request,
            provider=_CrashingBenchmarkProvider(),
        )
        degraded_errors = sorted(validator.iter_errors(degraded_result), key=lambda error: error.json_path)
        degraded_fallback_case_count += 1
        degraded_fallback_valid_count += int(
            not degraded_errors and degraded_result["analysis_updates"]["fallback_invocation_was_correct"] is True
        )

        abnormal_execution = run_investigation_runtime(
            packet,
            decision,
            config_path=repo_root / "configs" / "escalation.yaml",
            local_provider=_DegradedResidentBenchmarkProvider(),
        )
        abnormal_errors = (
            sorted(validator.iter_errors(abnormal_execution.final_result), key=lambda error: error.json_path)
            if abnormal_execution.final_result is not None
            else [ValueError("missing final result")]
        )
        direct_runtime_abnormal_fallback_case_count += 1
        direct_runtime_abnormal_fallback_valid_count += int(
            not abnormal_errors
            and abnormal_execution.final_result is not None
            and abnormal_execution.final_result["investigator_tier"] == "cloud_fallback_investigator"
            and abnormal_execution.cloud_plan is not None
            and abnormal_execution.cloud_plan.trigger_reasons == ("local_primary_degraded_fallback_to_cloud",)
        )

        warning_worker_recovery_wait_case_count += 1
        try:
            run_investigation_runtime(
                packet,
                decision,
                config_path=repo_root / "configs" / "escalation.yaml",
                local_provider=_DegradedResidentBenchmarkProvider(),
                runtime_context="warning_worker",
            )
        except LocalPrimaryRecoveryRequired as exc:
            warning_worker_recovery_wait_valid_count += int(
                exc.signal.abnormal_path.action == "queue_wait_for_local_primary_recovery"
            )

    total_cases = len(corpus)
    metrics = {
        "total_cases": total_cases,
        "expected_investigation_case_count": corpus_contract["expected_investigation_case_count"],
        "actual_local_primary_invocation_count": invocation_count,
        "local_primary_invocation_rate": round(invocation_count / total_cases, 2) if total_cases else 0.0,
        "routing_label_alignment_rate": round(routing_label_match_count / total_cases, 2) if total_cases else 0.0,
        "local_primary_p95_wall_time_sec": _p95(wall_times),
        "average_tool_calls_per_investigation": round(tool_calls_total / invocation_count, 2) if invocation_count else 0.0,
        "structured_completeness_rate": round(structured_complete_count / invocation_count, 2) if invocation_count else 0.0,
        "degraded_fallback_case_count": degraded_fallback_case_count,
        "degraded_fallback_validity_rate": round(
            degraded_fallback_valid_count / degraded_fallback_case_count, 2
        )
        if degraded_fallback_case_count
        else 0.0,
        "direct_runtime_abnormal_fallback_case_count": direct_runtime_abnormal_fallback_case_count,
        "direct_runtime_abnormal_fallback_validity_rate": round(
            direct_runtime_abnormal_fallback_valid_count / direct_runtime_abnormal_fallback_case_count,
            2,
        )
        if direct_runtime_abnormal_fallback_case_count
        else 0.0,
        "warning_worker_recovery_wait_case_count": warning_worker_recovery_wait_case_count,
        "warning_worker_recovery_wait_validity_rate": round(
            warning_worker_recovery_wait_valid_count / warning_worker_recovery_wait_case_count,
            2,
        )
        if warning_worker_recovery_wait_case_count
        else 0.0,
    }

    gates = benchmark_gate_snapshot(thresholds, config)
    acceptance = evaluate_local_primary_acceptance(
        corpus_contract=corpus_contract,
        metrics=metrics,
        gate_snapshot=gates,
    )

    notes: list[str] = []
    if schema_version == CALIBRATION_CORPUS_SCHEMA_VERSION:
        notes.append(
            "borrowed calibration corpus used; dedicated local-primary routing-eval corpus is still required for honest P4 closeout"
        )
    if metrics["routing_label_alignment_rate"] < 1.0:
        notes.append("current routing does not yet fully align with dedicated local-primary routing labels")
    if metrics["average_tool_calls_per_investigation"] == 0.0:
        notes.append("tool call metric currently reflects zero live wrapper invocations in the smoke provider")

    summary: BenchmarkSummary = {
        "summary_version": BENCHMARK_SUMMARY_VERSION,
        "generated_at": _utc_now(),
        "corpus_path": str(Path(corpus_path)),
        "corpus_contract": corpus_contract,
        "routing_snapshot": routing_snapshot(config),
        "gate_snapshot": gates,
        "metrics": metrics,
        "acceptance": acceptance,
        "accepted_local_primary_baseline": acceptance["accepted"],
        "notes": notes,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary
