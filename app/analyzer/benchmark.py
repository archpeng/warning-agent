"""Benchmark harness for the warning-agent local analyzer baseline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict

from app.analyzer.base import AnalyzerThresholds, load_thresholds
from app.analyzer.calibrate import (
    CorpusSufficiency,
    build_calibration_summary,
    load_calibration_corpus,
)
from app.analyzer.runtime import resolve_runtime_scorer

SEVERE_RECALL_MIN: Final = 0.85
TOP10_INVESTIGATION_PRECISION_MIN: Final = 0.60
INVESTIGATION_CANDIDATE_RATE_MAX: Final = 0.35


class AcceptanceCheck(TypedDict):
    actual: float | bool
    expected: float | bool
    comparator: str
    passed: bool


class BaselineAcceptance(TypedDict):
    accepted: bool
    blockers: list[str]
    checks: dict[str, AcceptanceCheck]


class BenchmarkGateSnapshot(TypedDict):
    sample_limited_must_be_false: bool
    minimum_calibration_cases: int
    minimum_severe_cases: int
    severe_recall_min: float
    top10_investigation_precision_min: float
    investigation_candidate_rate_max: float


class BenchmarkSummary(TypedDict):
    summary_version: str
    generated_at: str
    corpus_path: str
    metrics: dict[str, float | int]
    threshold_snapshot: dict[str, float | int | dict[str, float]]
    corpus_sufficiency: CorpusSufficiency
    acceptance_gate_snapshot: BenchmarkGateSnapshot
    acceptance: BaselineAcceptance
    sample_limited: bool
    accepted_baseline: bool
    notes: list[str]


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def benchmark_gate_snapshot(thresholds: AnalyzerThresholds) -> BenchmarkGateSnapshot:
    return {
        'sample_limited_must_be_false': True,
        'minimum_calibration_cases': thresholds.minimum_calibration_cases,
        'minimum_severe_cases': thresholds.minimum_severe_cases,
        'severe_recall_min': SEVERE_RECALL_MIN,
        'top10_investigation_precision_min': TOP10_INVESTIGATION_PRECISION_MIN,
        'investigation_candidate_rate_max': INVESTIGATION_CANDIDATE_RATE_MAX,
    }


def _metric_check(*, actual: float | bool, expected: float | bool, comparator: str, passed: bool) -> AcceptanceCheck:
    return {
        'actual': actual,
        'expected': expected,
        'comparator': comparator,
        'passed': passed,
    }


def _investigation_precision(summary: dict[str, object]) -> float:
    if 'top10_investigation_precision' in summary:
        return float(summary['top10_investigation_precision'])
    return float(summary['investigation_precision'])


def evaluate_baseline_acceptance(summary: dict[str, object], thresholds: AnalyzerThresholds) -> BaselineAcceptance:
    gates = benchmark_gate_snapshot(thresholds)
    sample_limited = bool(summary['sample_limited'])
    severe_recall = float(summary['severe_recall'])
    investigation_precision = _investigation_precision(summary)
    investigation_candidate_rate = float(summary['investigation_candidate_rate'])

    checks: dict[str, AcceptanceCheck] = {
        'corpus_sufficient': _metric_check(
            actual=not sample_limited,
            expected=True,
            comparator='==',
            passed=not sample_limited,
        ),
        'severe_recall': _metric_check(
            actual=severe_recall,
            expected=gates['severe_recall_min'],
            comparator='>=',
            passed=severe_recall >= gates['severe_recall_min'],
        ),
        'top10_investigation_precision': _metric_check(
            actual=investigation_precision,
            expected=gates['top10_investigation_precision_min'],
            comparator='>=',
            passed=investigation_precision >= gates['top10_investigation_precision_min'],
        ),
        'investigation_candidate_rate': _metric_check(
            actual=investigation_candidate_rate,
            expected=gates['investigation_candidate_rate_max'],
            comparator='<=',
            passed=investigation_candidate_rate <= gates['investigation_candidate_rate_max'],
        ),
    }

    blockers: list[str] = []
    if not checks['corpus_sufficient']['passed']:
        blockers.append('corpus_sample_limited')
    if not checks['severe_recall']['passed']:
        blockers.append('severe_recall_below_gate')
    if not checks['top10_investigation_precision']['passed']:
        blockers.append('investigation_precision_below_gate')
    if not checks['investigation_candidate_rate']['passed']:
        blockers.append('investigation_candidate_rate_above_gate')

    return {
        'accepted': not blockers,
        'blockers': blockers,
        'checks': checks,
    }


def run_local_analyzer_benchmark(
    *,
    corpus_path: str | Path,
    output_path: str | Path,
    repo_root: Path = Path('.'),
) -> BenchmarkSummary:
    thresholds = load_thresholds(repo_root / 'configs/thresholds.yaml')
    scorer = resolve_runtime_scorer(repo_root=repo_root, thresholds=thresholds)
    corpus_path = Path(corpus_path)
    calibration_summary = build_calibration_summary(
        load_calibration_corpus(corpus_path),
        scorer=scorer,
        thresholds=thresholds,
        repo_root=repo_root,
    )
    acceptance = evaluate_baseline_acceptance(calibration_summary, thresholds)

    benchmark: BenchmarkSummary = {
        'summary_version': 'local-analyzer-benchmark-summary.v1',
        'generated_at': _utc_now(),
        'corpus_path': str(corpus_path),
        'metrics': {
            'total_cases': calibration_summary['total_cases'],
            'severe_case_count': calibration_summary['severe_case_count'],
            'predicted_severe_count': calibration_summary['predicted_severe_count'],
            'predicted_investigation_count': calibration_summary['predicted_investigation_count'],
            'severe_recall': calibration_summary['severe_recall'],
            'top10_investigation_precision': calibration_summary['investigation_precision'],
            'investigation_candidate_rate': calibration_summary['investigation_candidate_rate'],
            'average_confidence': calibration_summary['average_confidence'],
        },
        'threshold_snapshot': calibration_summary['threshold_snapshot'],
        'corpus_sufficiency': calibration_summary['corpus_sufficiency'],
        'acceptance_gate_snapshot': benchmark_gate_snapshot(thresholds),
        'acceptance': acceptance,
        'sample_limited': calibration_summary['sample_limited'],
        'accepted_baseline': acceptance['accepted'],
        'notes': calibration_summary['notes'],
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return benchmark
