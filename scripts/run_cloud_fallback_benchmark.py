from __future__ import annotations

from pathlib import Path

from app.investigator.cloud_benchmark import run_cloud_fallback_benchmark


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "fixtures" / "evidence" / "cloud-fallback-routing-eval-corpus.json"
OUTPUT_PATH = REPO_ROOT / "data" / "benchmarks" / "cloud-fallback-baseline-summary.json"


if __name__ == "__main__":
    summary = run_cloud_fallback_benchmark(
        corpus_path=CORPUS_PATH,
        output_path=OUTPUT_PATH,
        repo_root=REPO_ROOT,
    )
    print(summary)
