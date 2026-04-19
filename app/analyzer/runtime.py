"""Runtime analyzer resolver for warning-agent."""

from __future__ import annotations

from pathlib import Path

from app.analyzer.base import AnalyzerThresholds, load_thresholds
from app.analyzer.fast_scorer import FastScorer
from app.analyzer.trained_scorer import DEFAULT_TRAINED_SCORER_ARTIFACT_PATH, TrainedScorer


def resolve_runtime_scorer(
    *,
    repo_root: str | Path = Path("."),
    thresholds: AnalyzerThresholds | None = None,
) -> FastScorer | TrainedScorer:
    repo_root = Path(repo_root)
    thresholds = thresholds or load_thresholds(repo_root / "configs" / "thresholds.yaml")
    artifact_path = repo_root / DEFAULT_TRAINED_SCORER_ARTIFACT_PATH

    if artifact_path.exists():
        try:
            return TrainedScorer.from_artifact_path(artifact_path, thresholds=thresholds)
        except ValueError:
            pass

    return FastScorer(thresholds)
