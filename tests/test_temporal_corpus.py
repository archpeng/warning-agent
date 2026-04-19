from __future__ import annotations

from pathlib import Path

from app.benchmarks.temporal_corpus import (
    TEMPORAL_ROBUSTNESS_CORPUS_SCHEMA_VERSION,
    load_temporal_robustness_corpus,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-temporal-robustness-corpus.json"


def test_load_temporal_robustness_corpus_freezes_minimal_variant_surface() -> None:
    schema_version, cases = load_temporal_robustness_corpus(CORPUS)

    assert schema_version == TEMPORAL_ROBUSTNESS_CORPUS_SCHEMA_VERSION
    assert len(cases) == 12
    assert all(len(case["variants"]) == 3 for case in cases)
    assert cases[0]["variants"][0]["time_offset_minutes"] == -5
    assert cases[0]["variants"][1]["temporal_context"]["anomaly_duration_sec"] == 900
    assert cases[2]["variants"][2]["expected_needs_investigation"] is False
