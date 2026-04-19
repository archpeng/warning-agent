from __future__ import annotations

from pathlib import Path
from pprint import pprint

from app.analyzer.trained_scorer import train_trained_scorer_artifact


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    artifact = train_trained_scorer_artifact(
        calibration_corpus_path=repo_root / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json",
        temporal_corpus_path=repo_root / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json",
        output_path=repo_root / "data" / "models" / "local-analyzer-trained-scorer.v1.json",
        repo_root=repo_root,
    )
    pprint(artifact)
