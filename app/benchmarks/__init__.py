"""Benchmark surface contracts for warning-agent trust upgrades."""

from app.benchmarks.contracts import (
    TRUST_BENCHMARK_SURFACES,
    BenchmarkSurfaceContract,
    build_surface_header,
    get_surface_contract,
)

__all__ = [
    "TRUST_BENCHMARK_SURFACES",
    "BenchmarkSurfaceContract",
    "build_surface_header",
    "get_surface_contract",
]
