"""Compatibility facade for trained local-analyzer scorer runtime and training surfaces."""

from app.analyzer.trained_scorer_runtime import (
    DEFAULT_TRAINED_SCORER_ARTIFACT_PATH,
    TRAINED_SCORER_ARTIFACT_VERSION,
    TRAINED_SCORER_CALIBRATION_METHOD,
    TRAINED_SCORER_MODEL_FAMILY,
    CalibrationParameters,
    TrainedScorer,
    TrainedScorerArtifact,
    build_temporal_context_from_packet,
    ensure_packet_v2,
    load_trained_scorer_artifact,
)
from app.analyzer.trained_scorer_training import train_trained_scorer_artifact

__all__ = [
    "CalibrationParameters",
    "DEFAULT_TRAINED_SCORER_ARTIFACT_PATH",
    "TRAINED_SCORER_ARTIFACT_VERSION",
    "TRAINED_SCORER_CALIBRATION_METHOD",
    "TRAINED_SCORER_MODEL_FAMILY",
    "TrainedScorer",
    "TrainedScorerArtifact",
    "build_temporal_context_from_packet",
    "ensure_packet_v2",
    "load_trained_scorer_artifact",
    "train_trained_scorer_artifact",
]
