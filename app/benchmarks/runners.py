"""Repeatable W3 benchmark runner scaffolds for warning-agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from app.analyzer.base import load_thresholds
from app.analyzer.calibrate import build_calibration_summary, load_calibration_corpus
from app.analyzer.runtime import resolve_runtime_scorer
from app.analyzer.temporal_features import TEMPORAL_FEATURE_SET_VERSION
from app.analyzer.versioning import FAST_SCORER_ANALYZER_VERSION, FAST_SCORER_FEATURE_SET_VERSION
from app.benchmarks.contracts import BenchmarkSurfaceId, build_surface_header, get_surface_contract
from app.benchmarks.temporal_corpus import load_temporal_robustness_corpus
from app.investigator.benchmark import run_local_primary_benchmark
from app.investigator.handoff_benchmark import run_local_handoff_benchmark

TEMPORAL_MIN_BASE_CASES: Final = 12
TEMPORAL_MIN_VARIANTS_PER_CASE: Final = 3
ROUTING_MIN_CASES: Final = 20
ROUTING_MIN_EXPECTED_LOCAL_PRIMARY_CASES: Final = 4
HANDOFF_MIN_CASES: Final = 12


class AcceptanceCheck(TypedDict):
    actual: float | bool
    expected: float | bool
    comparator: str
    passed: bool


class SurfaceAcceptance(TypedDict):
    accepted: bool
    blockers: list[str]
    checks: dict[str, AcceptanceCheck]


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _metric_check(*, actual: float | bool, expected: float | bool, comparator: str, passed: bool) -> AcceptanceCheck:
    return {
        "actual": actual,
        "expected": expected,
        "comparator": comparator,
        "passed": passed,
    }


def _measurement_acceptance(measurement_ready: bool) -> SurfaceAcceptance:
    check = _metric_check(actual=measurement_ready, expected=True, comparator="==", passed=measurement_ready)
    blockers = [] if measurement_ready else ["benchmark_measurement_not_ready"]
    return {
        "accepted": measurement_ready,
        "blockers": blockers,
        "checks": {"benchmark_measurement_ready": check},
    }


def _write_summary(summary: dict[str, object], *, output_path: Path) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_local_analyzer_calibration_surface(
    *,
    repo_root: Path,
    corpus_path: Path,
    output_path: Path,
) -> dict[str, object]:
    thresholds = load_thresholds(repo_root / "configs" / "thresholds.yaml")
    scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=thresholds)
    summary = build_calibration_summary(
        load_calibration_corpus(corpus_path),
        scorer=scorer,
        thresholds=thresholds,
        repo_root=repo_root,
    )
    return _write_summary(summary, output_path=output_path)


def run_local_analyzer_temporal_robustness_scaffold(
    *,
    repo_root: Path,
    output_path: Path,
    corpus_path: Path | None = None,
) -> dict[str, object]:
    blockers: list[str] = []
    total_base_cases = 0
    variants_per_case = 0
    schema_version = None
    if corpus_path is None or not corpus_path.exists():
        blockers.append("temporal_robustness_corpus_missing")
    else:
        schema_version, cases = load_temporal_robustness_corpus(corpus_path)
        total_base_cases = len(cases)
        variants_per_case = min((len(case["variants"]) for case in cases), default=0)
        if total_base_cases < TEMPORAL_MIN_BASE_CASES:
            blockers.append("temporal_robustness_cases_below_w3_minimum")
        if variants_per_case < TEMPORAL_MIN_VARIANTS_PER_CASE:
            blockers.append("temporal_robustness_variants_below_w3_minimum")

    measurement_ready = not blockers
    summary = {
        **build_surface_header(
            "local_analyzer_temporal_robustness",
            feature_set_version=FAST_SCORER_FEATURE_SET_VERSION,
            analyzer_version=FAST_SCORER_ANALYZER_VERSION,
        ),
        "generated_at": _utc_now(),
        "corpus_path": str(corpus_path) if corpus_path else None,
        "corpus_contract": {
            "schema_version": schema_version,
            "minimum_base_cases": TEMPORAL_MIN_BASE_CASES,
            "minimum_variants_per_case": TEMPORAL_MIN_VARIANTS_PER_CASE,
            "total_base_cases": total_base_cases,
            "minimum_variants_observed": variants_per_case,
            "measurement_ready": measurement_ready,
            "blocking_reasons": blockers,
        },
        "metrics": {
            "total_base_cases": total_base_cases,
            "minimum_variants_observed": variants_per_case,
        },
        "acceptance": _measurement_acceptance(measurement_ready),
        "notes": [
            "scaffold summary only; temporal robustness corpus is not yet materialized to W3 planning minima"
        ],
    }
    return _write_summary(summary, output_path=output_path)


def run_local_routing_correctness_scaffold(
    *,
    repo_root: Path,
    corpus_path: Path,
    output_path: Path,
) -> dict[str, object]:
    benchmark = run_local_primary_benchmark(
        corpus_path=corpus_path,
        output_path=output_path,
        repo_root=repo_root,
    )
    scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=load_thresholds(repo_root / "configs/thresholds.yaml"))
    routing_alignment = float(benchmark["metrics"]["routing_label_alignment_rate"])
    measurement_ready = bool(benchmark["corpus_contract"]["measurement_ready"])

    summary = {
        **build_surface_header(
            "local_routing_correctness",
            feature_set_version=TEMPORAL_FEATURE_SET_VERSION,
            analyzer_version=scorer.analyzer_version,
        ),
        "generated_at": _utc_now(),
        "corpus_path": str(corpus_path),
        "corpus_contract": {
            "schema_version": benchmark["corpus_contract"]["schema_version"],
            "minimum_cases": ROUTING_MIN_CASES,
            "minimum_expected_local_primary_cases": ROUTING_MIN_EXPECTED_LOCAL_PRIMARY_CASES,
            "measurement_ready": measurement_ready,
            "blocking_reasons": list(benchmark["corpus_contract"]["blocking_reasons"]),
        },
        "metrics": {
            "total_cases": benchmark["metrics"]["total_cases"],
            "expected_local_primary_case_count": benchmark["metrics"]["expected_investigation_case_count"],
            "actual_local_primary_invocation_count": benchmark["metrics"]["actual_local_primary_invocation_count"],
            "routing_label_alignment_rate": routing_alignment,
        },
        "acceptance": {
            "accepted": bool(measurement_ready and routing_alignment == 1.0),
            "blockers": [
                *([] if measurement_ready else ["benchmark_measurement_not_ready"]),
                *([] if routing_alignment == 1.0 else ["routing_label_alignment_below_gate"]),
            ],
            "checks": {
                "benchmark_measurement_ready": _metric_check(
                    actual=measurement_ready,
                    expected=True,
                    comparator="==",
                    passed=measurement_ready,
                ),
                "routing_label_alignment_rate": _metric_check(
                    actual=routing_alignment,
                    expected=1.0,
                    comparator="==",
                    passed=routing_alignment == 1.0,
                ),
            },
        },
        "notes": [
            "trained scorer routing benchmark reflects actual local-primary routing alignment on the dedicated routing corpus"
        ],
    }
    return _write_summary(summary, output_path=output_path)


def run_local_handoff_quality_scaffold(
    *,
    repo_root: Path,
    output_path: Path,
    corpus_path: Path | None = None,
) -> dict[str, object]:
    if corpus_path is None or not corpus_path.exists():
        blockers = ["handoff_eval_corpus_missing"]
        summary = {
            **build_surface_header(
                "local_handoff_quality",
                feature_set_version=TEMPORAL_FEATURE_SET_VERSION,
                analyzer_version=resolve_runtime_scorer(
                    repo_root=repo_root,
                    thresholds=load_thresholds(repo_root / "configs/thresholds.yaml"),
                ).analyzer_version,
            ),
            "generated_at": _utc_now(),
            "corpus_path": str(corpus_path) if corpus_path else None,
            "corpus_contract": {
                "schema_version": None,
                "minimum_cases": HANDOFF_MIN_CASES,
                "measurement_ready": False,
                "blocking_reasons": blockers,
            },
            "metrics": {
                "total_cases": 0,
                "expected_cloud_fallback_case_count": 0,
                "actual_cloud_fallback_case_count": 0,
                "handoff_target_alignment_rate": 0.0,
                "carry_reason_code_alignment_rate": 0.0,
            },
            "acceptance": {
                "accepted": False,
                "blockers": ["benchmark_measurement_not_ready"],
                "checks": {
                    "benchmark_measurement_ready": _metric_check(
                        actual=False,
                        expected=True,
                        comparator="==",
                        passed=False,
                    ),
                    "handoff_target_alignment_rate": _metric_check(
                        actual=0.0,
                        expected=1.0,
                        comparator="==",
                        passed=False,
                    ),
                    "carry_reason_code_alignment_rate": _metric_check(
                        actual=0.0,
                        expected=1.0,
                        comparator="==",
                        passed=False,
                    ),
                },
            },
            "notes": ["scaffold summary only; handoff-eval corpus has not been materialized yet"],
        }
        return _write_summary(summary, output_path=output_path)

    benchmark = run_local_handoff_benchmark(corpus_path=corpus_path, repo_root=repo_root)
    summary = {
        **build_surface_header(
            "local_handoff_quality",
            feature_set_version=TEMPORAL_FEATURE_SET_VERSION,
            analyzer_version=benchmark["analyzer_version"],
        ),
        "generated_at": _utc_now(),
        "corpus_path": str(corpus_path),
        "corpus_contract": benchmark["corpus_contract"],
        "metrics": benchmark["metrics"],
        "acceptance": benchmark["acceptance"],
        "notes": benchmark["notes"],
    }
    return _write_summary(summary, output_path=output_path)


def run_trust_benchmark_surface(
    surface_id: BenchmarkSurfaceId,
    *,
    repo_root: Path = Path("."),
    corpus_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, object]:
    repo_root = Path(repo_root)
    contract = get_surface_contract(surface_id)
    output_path = output_path or contract.output_path

    if surface_id == "local_analyzer_calibration":
        return run_local_analyzer_calibration_surface(
            repo_root=repo_root,
            corpus_path=Path(corpus_path or repo_root / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"),
            output_path=output_path,
        )
    if surface_id == "local_analyzer_temporal_robustness":
        return run_local_analyzer_temporal_robustness_scaffold(
            repo_root=repo_root,
            corpus_path=Path(
                corpus_path or repo_root / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json"
            ),
            output_path=output_path,
        )
    if surface_id == "local_routing_correctness":
        return run_local_routing_correctness_scaffold(
            repo_root=repo_root,
            corpus_path=Path(corpus_path or repo_root / "fixtures" / "evidence" / "local-primary-routing-eval-corpus.json"),
            output_path=output_path,
        )
    if surface_id == "local_handoff_quality":
        return run_local_handoff_quality_scaffold(
            repo_root=repo_root,
            corpus_path=Path(corpus_path or repo_root / "fixtures" / "evidence" / "local-handoff-eval-corpus.json"),
            output_path=output_path,
        )

    raise KeyError(f"unsupported benchmark surface: {surface_id}")
