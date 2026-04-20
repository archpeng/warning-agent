from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.base import load_thresholds
from app.investigator.benchmark import (
    ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
    benchmark_gate_snapshot,
    evaluate_local_primary_acceptance,
    run_local_primary_benchmark,
)
from app.investigator.router import load_investigator_routing_config


REPO_ROOT = Path(__file__).resolve().parents[1]
BORROWED_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"
DEDICATED_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-primary-routing-eval-corpus.json"


def test_local_primary_benchmark_writes_scaffold_summary_for_borrowed_calibration_corpus(tmp_path: Path) -> None:
    output_path = tmp_path / "local-primary-baseline-summary.json"

    summary = run_local_primary_benchmark(
        corpus_path=BORROWED_CORPUS,
        output_path=output_path,
        repo_root=REPO_ROOT,
    )

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary == written
    assert summary["summary_version"] == "local-primary-benchmark-summary.v1"
    assert summary["metrics"]["total_cases"] == 30
    assert summary["metrics"]["expected_investigation_case_count"] == 8
    assert summary["metrics"]["actual_local_primary_invocation_count"] == 6
    assert summary["metrics"]["local_primary_invocation_rate"] == 0.2
    assert summary["metrics"]["routing_label_alignment_rate"] == 0.93
    assert summary["metrics"]["average_tool_calls_per_investigation"] == 1.0
    assert summary["metrics"]["structured_completeness_rate"] == 1.0
    assert summary["metrics"]["degraded_fallback_validity_rate"] == 1.0
    assert summary["metrics"]["direct_runtime_abnormal_fallback_validity_rate"] == 1.0
    assert summary["metrics"]["warning_worker_recovery_wait_validity_rate"] == 1.0
    assert summary["corpus_contract"]["schema_version"] == "local-analyzer-calibration-corpus.v1"
    assert summary["corpus_contract"]["measurement_ready"] is False
    assert summary["corpus_contract"]["blocking_reasons"] == ["dedicated_routing_eval_corpus_missing"]
    assert summary["acceptance"]["accepted"] is False
    assert summary["acceptance"]["blockers"] == ["benchmark_measurement_not_ready"]
    assert summary["accepted_local_primary_baseline"] is False
    assert any("dedicated local-primary routing-eval corpus" in note for note in summary["notes"])


def test_local_primary_benchmark_marks_dedicated_corpus_closeout_ready_after_routing_recovery() -> None:
    summary = run_local_primary_benchmark(
        corpus_path=DEDICATED_CORPUS,
        output_path=Path("/tmp/local-primary-baseline-summary.json"),
        repo_root=REPO_ROOT,
    )

    assert summary["corpus_contract"]["schema_version"] == ROUTING_EVAL_CORPUS_SCHEMA_VERSION
    assert summary["corpus_contract"]["measurement_ready"] is True
    assert summary["corpus_contract"]["blocking_reasons"] == []
    assert summary["metrics"]["total_cases"] == 20
    assert summary["metrics"]["expected_investigation_case_count"] == 4
    assert summary["metrics"]["actual_local_primary_invocation_count"] == 4
    assert summary["metrics"]["local_primary_invocation_rate"] == 0.2
    assert summary["metrics"]["routing_label_alignment_rate"] == 1.0
    assert summary["metrics"]["average_tool_calls_per_investigation"] == 1.0
    assert summary["metrics"]["direct_runtime_abnormal_fallback_validity_rate"] == 1.0
    assert summary["metrics"]["warning_worker_recovery_wait_validity_rate"] == 1.0
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["blockers"] == []
    assert summary["accepted_local_primary_baseline"] is True


def test_evaluate_local_primary_acceptance_accepts_closeout_ready_metrics() -> None:
    thresholds = load_thresholds(REPO_ROOT / "configs" / "thresholds.yaml")
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    acceptance = evaluate_local_primary_acceptance(
        corpus_contract={
            "schema_version": ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
            "total_cases": 10,
            "expected_investigation_case_count": 2,
            "minimum_cases": thresholds.minimum_calibration_cases,
            "minimum_investigation_cases": 2,
            "measurement_ready": True,
            "blocking_reasons": [],
        },
        metrics={
            "total_cases": 10,
            "expected_investigation_case_count": 2,
            "actual_local_primary_invocation_count": 2,
            "local_primary_invocation_rate": 0.2,
            "routing_label_alignment_rate": 1.0,
            "local_primary_p95_wall_time_sec": 12.4,
            "average_tool_calls_per_investigation": 3.0,
            "structured_completeness_rate": 1.0,
            "degraded_fallback_case_count": 2,
            "degraded_fallback_validity_rate": 1.0,
            "direct_runtime_abnormal_fallback_case_count": 2,
            "direct_runtime_abnormal_fallback_validity_rate": 1.0,
            "warning_worker_recovery_wait_case_count": 2,
            "warning_worker_recovery_wait_validity_rate": 1.0,
        },
        gate_snapshot=benchmark_gate_snapshot(thresholds, config),
    )

    assert acceptance["accepted"] is True
    assert acceptance["blockers"] == []
    assert all(check["passed"] is True for check in acceptance["checks"].values())
