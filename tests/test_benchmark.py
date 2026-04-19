from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.base import load_thresholds
from app.analyzer.benchmark import evaluate_baseline_acceptance, run_local_analyzer_benchmark


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / 'fixtures' / 'evidence' / 'local-analyzer-calibration-corpus.json'


def test_evaluate_baseline_acceptance_reports_scaffold_and_metric_blockers() -> None:
    thresholds = load_thresholds()

    acceptance = evaluate_baseline_acceptance(
        {
            'sample_limited': True,
            'severe_recall': 1.0,
            'investigation_precision': 1.0,
            'investigation_candidate_rate': 0.5,
        },
        thresholds,
    )

    assert acceptance['accepted'] is False
    assert acceptance['blockers'] == [
        'corpus_sample_limited',
        'investigation_candidate_rate_above_gate',
    ]
    assert acceptance['checks']['corpus_sufficient']['passed'] is False
    assert acceptance['checks']['severe_recall']['passed'] is True
    assert acceptance['checks']['top10_investigation_precision']['passed'] is True
    assert acceptance['checks']['investigation_candidate_rate']['passed'] is False


def test_evaluate_baseline_acceptance_accepts_closeout_ready_metrics() -> None:
    thresholds = load_thresholds()

    acceptance = evaluate_baseline_acceptance(
        {
            'sample_limited': False,
            'severe_recall': 0.9,
            'investigation_precision': 0.7,
            'investigation_candidate_rate': 0.35,
        },
        thresholds,
    )

    assert acceptance['accepted'] is True
    assert acceptance['blockers'] == []
    assert all(check['passed'] is True for check in acceptance['checks'].values())


def test_benchmark_harness_writes_summary_for_closeout_ready_corpus(tmp_path: Path) -> None:
    output_path = tmp_path / 'local-analyzer-baseline-summary.json'

    summary = run_local_analyzer_benchmark(
        corpus_path=CORPUS,
        output_path=output_path,
        repo_root=REPO_ROOT,
    )

    written = json.loads(output_path.read_text(encoding='utf-8'))
    assert summary == written
    assert summary['summary_version'] == 'local-analyzer-benchmark-summary.v1'
    assert summary['metrics']['total_cases'] == 30
    assert summary['metrics']['severe_case_count'] == 8
    assert summary['metrics']['severe_recall'] >= 0.85
    assert summary['metrics']['top10_investigation_precision'] >= 0.6
    assert summary['metrics']['investigation_candidate_rate'] <= 0.35
    assert summary['sample_limited'] is False
    assert summary['accepted_baseline'] is True
    assert summary['corpus_sufficiency']['ready'] is True
    assert summary['acceptance_gate_snapshot']['minimum_calibration_cases'] == 10
    assert summary['acceptance_gate_snapshot']['minimum_severe_cases'] == 3
    assert summary['acceptance']['accepted'] is True
    assert summary['acceptance']['blockers'] == []
    assert all(check['passed'] is True for check in summary['acceptance']['checks'].values())
