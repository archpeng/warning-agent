from __future__ import annotations

from pathlib import Path

from app.investigator.cloud_benchmark import (
    CLOUD_BENCHMARK_SUMMARY_VERSION,
    CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
    cloud_benchmark_gate_snapshot,
    evaluate_cloud_fallback_benchmark_acceptance,
    run_cloud_fallback_benchmark,
)
from app.investigator.router import load_investigator_routing_config


REPO_ROOT = Path(__file__).resolve().parents[1]
BORROWED_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-primary-routing-eval-corpus.json"
DEDICATED_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "cloud-fallback-routing-eval-corpus.json"


def test_cloud_benchmark_marks_borrowed_local_primary_corpus_not_measurement_ready(tmp_path: Path) -> None:
    output_path = tmp_path / "cloud-fallback-baseline-summary.json"

    summary = run_cloud_fallback_benchmark(
        corpus_path=BORROWED_CORPUS,
        output_path=output_path,
        repo_root=REPO_ROOT,
    )

    assert summary["summary_version"] == CLOUD_BENCHMARK_SUMMARY_VERSION
    assert summary["corpus_contract"]["schema_version"] == "local-primary-routing-eval-corpus.v1"
    assert summary["corpus_contract"]["measurement_ready"] is False
    assert summary["corpus_contract"]["blocking_reasons"] == ["dedicated_cloud_routing_eval_corpus_missing"]
    assert summary["acceptance"]["accepted"] is False
    assert summary["acceptance"]["blockers"] == ["benchmark_measurement_not_ready"]


def test_cloud_benchmark_accepts_dedicated_corpus_and_reports_p5_gate_evidence(tmp_path: Path) -> None:
    output_path = tmp_path / "cloud-fallback-baseline-summary.json"

    summary = run_cloud_fallback_benchmark(
        corpus_path=DEDICATED_CORPUS,
        output_path=output_path,
        repo_root=REPO_ROOT,
    )

    assert summary["summary_version"] == CLOUD_BENCHMARK_SUMMARY_VERSION
    assert summary["corpus_contract"]["schema_version"] == CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION
    assert summary["corpus_contract"]["measurement_ready"] is True
    assert summary["metrics"]["actual_cloud_fallback_invocation_count"] == 0
    assert summary["metrics"]["cloud_fallback_rate_total"] == 0.0
    assert summary["metrics"]["cloud_fallback_rate_investigated"] == 0.0
    assert summary["metrics"]["final_investigation_schema_validity_rate"] == 1.0
    assert summary["metrics"]["cloud_unavailable_fallback_report_success_rate"] == 1.0
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["blockers"] == []
    assert summary["accepted_cloud_fallback_baseline"] is True


def test_evaluate_cloud_benchmark_acceptance_detects_gate_regressions() -> None:
    config = load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml")

    acceptance = evaluate_cloud_fallback_benchmark_acceptance(
        corpus_contract={
            "schema_version": CLOUD_ROUTING_EVAL_CORPUS_SCHEMA_VERSION,
            "total_cases": 10,
            "expected_cloud_fallback_case_count": 0,
            "minimum_cases": 10,
            "measurement_ready": True,
            "blocking_reasons": [],
        },
        metrics={
            "total_cases": 10,
            "actual_cloud_fallback_invocation_count": 2,
            "investigated_case_count": 4,
            "cloud_fallback_rate_total": 0.2,
            "cloud_fallback_rate_investigated": 0.5,
            "cloud_fallback_p95_wall_time_sec": 95.0,
            "compressed_handoff_p95_tokens": 1400,
            "final_investigation_schema_validity_rate": 0.9,
            "cloud_unavailable_fallback_report_success_rate": 0.5,
        },
        gate_snapshot=cloud_benchmark_gate_snapshot(config),
    )

    assert acceptance["accepted"] is False
    assert set(acceptance["blockers"]) == {
        "cloud_fallback_rate_total_above_gate",
        "cloud_fallback_rate_investigated_above_gate",
        "cloud_fallback_wall_time_above_gate",
        "compressed_handoff_tokens_above_gate",
        "final_investigation_schema_invalid",
        "cloud_unavailable_fallback_report_success_below_gate",
    }
