"""Frozen W3 benchmark surface contracts for warning-agent local trust work."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from app.contracts_common import DATA_DIR

BenchmarkSurfaceId = Literal[
    "local_analyzer_calibration",
    "local_analyzer_temporal_robustness",
    "local_routing_correctness",
    "local_handoff_quality",
]

RUNNER_INTERFACE_VERSION: Final = "warning-agent-trust-benchmark-runner.v1"


@dataclass(frozen=True)
class BenchmarkSurfaceContract:
    surface_id: BenchmarkSurfaceId
    summary_version: str
    output_path: Path
    runner_slug: str
    required_version_fields: tuple[str, str, str, str] = (
        "summary_version",
        "feature_set_version",
        "analyzer_version",
        "runner_version",
    )


TRUST_BENCHMARK_SURFACES: Final[tuple[BenchmarkSurfaceContract, ...]] = (
    BenchmarkSurfaceContract(
        surface_id="local_analyzer_calibration",
        summary_version="local-analyzer-calibration-summary.v1",
        output_path=DATA_DIR / "benchmarks" / "local-analyzer-calibration-summary.json",
        runner_slug="local-analyzer-calibration",
    ),
    BenchmarkSurfaceContract(
        surface_id="local_analyzer_temporal_robustness",
        summary_version="local-analyzer-temporal-robustness-summary.v1",
        output_path=DATA_DIR / "benchmarks" / "local-analyzer-temporal-robustness-summary.json",
        runner_slug="local-analyzer-temporal-robustness",
    ),
    BenchmarkSurfaceContract(
        surface_id="local_routing_correctness",
        summary_version="local-routing-correctness-summary.v1",
        output_path=DATA_DIR / "benchmarks" / "local-routing-correctness-summary.json",
        runner_slug="local-routing-correctness",
    ),
    BenchmarkSurfaceContract(
        surface_id="local_handoff_quality",
        summary_version="local-handoff-quality-summary.v1",
        output_path=DATA_DIR / "benchmarks" / "local-handoff-quality-summary.json",
        runner_slug="local-handoff-quality",
    ),
)


def get_surface_contract(surface_id: BenchmarkSurfaceId) -> BenchmarkSurfaceContract:
    for surface in TRUST_BENCHMARK_SURFACES:
        if surface.surface_id == surface_id:
            return surface
    raise KeyError(f"unknown benchmark surface: {surface_id}")


def build_surface_header(
    surface_id: BenchmarkSurfaceId,
    *,
    feature_set_version: str,
    analyzer_version: str,
) -> dict[str, str]:
    contract = get_surface_contract(surface_id)
    return {
        "summary_version": contract.summary_version,
        "feature_set_version": feature_set_version,
        "analyzer_version": analyzer_version,
        "runner_version": RUNNER_INTERFACE_VERSION,
    }
