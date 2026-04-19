from __future__ import annotations

import json
from pathlib import Path

from app.analyzer.training_scaffold import run_trained_scorer_scaffold


def main() -> int:
    repo_root = Path('.')
    summary = run_trained_scorer_scaffold(
        calibration_corpus_path=repo_root / 'fixtures' / 'evidence' / 'local-analyzer-calibration-corpus.json',
        temporal_corpus_path=repo_root / 'fixtures' / 'evidence' / 'local-analyzer-temporal-robustness-corpus.json',
        summary_output_path=repo_root / 'data' / 'benchmarks' / 'local-analyzer-training-scaffold-summary.json',
        artifact_output_path=repo_root / 'data' / 'models' / 'local-analyzer-trained-scorer.scaffold.json',
        repo_root=repo_root,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
