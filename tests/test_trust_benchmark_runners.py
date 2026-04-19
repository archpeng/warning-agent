from __future__ import annotations

import json
from pathlib import Path

from app.benchmarks.runners import run_trust_benchmark_surface


REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"
ROUTING_CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-primary-routing-eval-corpus.json"


def test_calibration_benchmark_runner_writes_summary_with_frozen_versions(tmp_path: Path) -> None:
    output_path = tmp_path / "local-analyzer-calibration-summary.json"

    summary = run_trust_benchmark_surface(
        "local_analyzer_calibration",
        repo_root=REPO_ROOT,
        corpus_path=CALIBRATION_CORPUS,
        output_path=output_path,
    )

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary == written
    assert summary["summary_version"] == "local-analyzer-calibration-summary.v1"
    assert summary["feature_set_version"] == "fast-scorer-baseline-features.v1"
    assert summary["analyzer_version"] == "trained-scorer-2026-04-19"
    assert summary["runner_version"] == "warning-agent-trust-benchmark-runner.v1"
    assert summary["gate_ready"] is True


def test_temporal_robustness_runner_scaffold_uses_minimal_corpus_and_reports_below_minimum_truthfully(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "local-analyzer-temporal-robustness-summary.json"
    corpus_path = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json"

    summary = run_trust_benchmark_surface(
        "local_analyzer_temporal_robustness",
        repo_root=REPO_ROOT,
        corpus_path=corpus_path,
        output_path=output_path,
    )

    assert summary["summary_version"] == "local-analyzer-temporal-robustness-summary.v1"
    assert summary["metrics"]["total_base_cases"] == 12
    assert summary["metrics"]["minimum_variants_observed"] == 3
    assert summary["corpus_contract"]["measurement_ready"] is True
    assert summary["corpus_contract"]["blocking_reasons"] == []
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["blockers"] == []


def test_local_routing_correctness_runner_scaffold_reports_ready_corpus_when_w3_minima_are_met(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "local-routing-correctness-summary.json"

    summary = run_trust_benchmark_surface(
        "local_routing_correctness",
        repo_root=REPO_ROOT,
        corpus_path=ROUTING_CORPUS,
        output_path=output_path,
    )

    assert summary["summary_version"] == "local-routing-correctness-summary.v1"
    assert summary["analyzer_version"] == "trained-scorer-2026-04-19"
    assert summary["metrics"]["total_cases"] == 20
    assert summary["metrics"]["expected_local_primary_case_count"] == 4
    assert summary["metrics"]["actual_local_primary_invocation_count"] == 4
    assert summary["metrics"]["routing_label_alignment_rate"] == 1.0
    assert summary["corpus_contract"]["measurement_ready"] is True
    assert summary["corpus_contract"]["blocking_reasons"] == []
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["checks"]["routing_label_alignment_rate"]["passed"] is True
    assert any("trained scorer routing benchmark" in note for note in summary["notes"])


def test_handoff_quality_runner_scaffold_reports_ready_corpus_when_w3_minima_are_met(tmp_path: Path) -> None:
    output_path = tmp_path / "local-handoff-quality-summary.json"

    summary = run_trust_benchmark_surface(
        "local_handoff_quality",
        repo_root=REPO_ROOT,
        output_path=output_path,
    )

    assert summary["summary_version"] == "local-handoff-quality-summary.v1"
    assert summary["analyzer_version"] == "trained-scorer-2026-04-19"
    assert summary["metrics"]["total_cases"] == 12
    assert summary["metrics"]["expected_cloud_fallback_case_count"] == 4
    assert summary["metrics"]["actual_cloud_fallback_case_count"] == 4
    assert summary["metrics"]["handoff_target_alignment_rate"] == 1.0
    assert summary["metrics"]["carry_reason_code_alignment_rate"] == 1.0
    assert summary["corpus_contract"]["measurement_ready"] is True
    assert summary["corpus_contract"]["blocking_reasons"] == []
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["checks"]["handoff_target_alignment_rate"]["passed"] is True
    assert summary["acceptance"]["checks"]["carry_reason_code_alignment_rate"]["passed"] is True
    assert any("handoff benchmark" in note for note in summary["notes"])
