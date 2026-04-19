from __future__ import annotations

from pathlib import Path

from app.benchmarks.contracts import (
    TRUST_BENCHMARK_SURFACES,
    build_surface_header,
    get_surface_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_w3_benchmark_surface_registry_freezes_summary_versions_output_paths_and_runner_slugs() -> None:
    assert [surface.surface_id for surface in TRUST_BENCHMARK_SURFACES] == [
        "local_analyzer_calibration",
        "local_analyzer_temporal_robustness",
        "local_routing_correctness",
        "local_handoff_quality",
    ]

    calibration = get_surface_contract("local_analyzer_calibration")
    temporal = get_surface_contract("local_analyzer_temporal_robustness")
    routing = get_surface_contract("local_routing_correctness")
    handoff = get_surface_contract("local_handoff_quality")

    assert calibration.summary_version == "local-analyzer-calibration-summary.v1"
    assert temporal.summary_version == "local-analyzer-temporal-robustness-summary.v1"
    assert routing.summary_version == "local-routing-correctness-summary.v1"
    assert handoff.summary_version == "local-handoff-quality-summary.v1"

    assert calibration.output_path == REPO_ROOT / "data" / "benchmarks" / "local-analyzer-calibration-summary.json"
    assert temporal.output_path == REPO_ROOT / "data" / "benchmarks" / "local-analyzer-temporal-robustness-summary.json"
    assert routing.output_path == REPO_ROOT / "data" / "benchmarks" / "local-routing-correctness-summary.json"
    assert handoff.output_path == REPO_ROOT / "data" / "benchmarks" / "local-handoff-quality-summary.json"

    assert calibration.runner_slug == "local-analyzer-calibration"
    assert temporal.runner_slug == "local-analyzer-temporal-robustness"
    assert routing.runner_slug == "local-routing-correctness"
    assert handoff.runner_slug == "local-handoff-quality"

    for surface in TRUST_BENCHMARK_SURFACES:
        assert surface.required_version_fields == (
            "summary_version",
            "feature_set_version",
            "analyzer_version",
            "runner_version",
        )


def test_build_surface_header_carries_required_w3_version_fields() -> None:
    header = build_surface_header(
        "local_routing_correctness",
        feature_set_version="temporal-context-v2.preview",
        analyzer_version="fast-scorer-2026-04-19",
    )

    assert header == {
        "summary_version": "local-routing-correctness-summary.v1",
        "feature_set_version": "temporal-context-v2.preview",
        "analyzer_version": "fast-scorer-2026-04-19",
        "runner_version": "warning-agent-trust-benchmark-runner.v1",
    }
