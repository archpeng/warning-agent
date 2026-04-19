from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.benchmarks.runners import run_trust_benchmark_surface


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one warning-agent W3 trust benchmark surface")
    parser.add_argument(
        "surface",
        choices=[
            "local_analyzer_calibration",
            "local_analyzer_temporal_robustness",
            "local_routing_correctness",
            "local_handoff_quality",
        ],
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--corpus-path", default=None)
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args()

    summary = run_trust_benchmark_surface(
        args.surface,
        repo_root=Path(args.repo_root),
        corpus_path=Path(args.corpus_path) if args.corpus_path else None,
        output_path=Path(args.output_path) if args.output_path else None,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
