from __future__ import annotations

from pathlib import Path

from app.investigator.benchmark import run_local_primary_benchmark


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_local_primary_benchmark(
        corpus_path=repo_root / "fixtures/evidence/local-primary-routing-eval-corpus.json",
        output_path=repo_root / "data/benchmarks/local-primary-baseline-summary.json",
        repo_root=repo_root,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
