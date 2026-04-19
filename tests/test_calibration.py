from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analyzer.base import load_thresholds
from app.analyzer.calibrate import (
    build_calibration_summary,
    evaluate_corpus_sufficiency,
    load_calibration_corpus,
)
from app.analyzer.fast_scorer import FastScorer


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "fixtures" / "evidence" / "local-analyzer-calibration-corpus.json"


def test_load_calibration_corpus_rejects_unknown_label(tmp_path: Path) -> None:
    invalid_corpus = {
        "schema_version": "local-analyzer-calibration-corpus.v1",
        "cases": [
            {
                "case_id": "catalog_unknown_label",
                "label": "unknown",
                "expected_needs_investigation": False,
                "replay_fixture": "fixtures/replay/manual-replay.catalog.latency-warning.json",
                "evidence_fixture": "fixtures/evidence/catalog.packet-input.json",
                "retrieval_hits": [],
            }
        ],
    }
    corpus_path = tmp_path / "invalid-calibration-corpus.json"
    corpus_path.write_text(json.dumps(invalid_corpus), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported label"):
        load_calibration_corpus(corpus_path)


def test_evaluate_corpus_sufficiency_marks_minimum_labeled_corpus_ready() -> None:
    thresholds = load_thresholds()
    corpus = [
        {
            "case_id": f"case_{index}",
            "label": "severe" if index < 3 else "benign",
            "expected_needs_investigation": index < 3,
            "replay_fixture": "fixtures/replay/manual-replay.checkout.high-error-rate.json",
            "evidence_fixture": "fixtures/evidence/checkout.packet-input.json",
            "retrieval_hits": [],
        }
        for index in range(10)
    ]

    sufficiency = evaluate_corpus_sufficiency(corpus, thresholds=thresholds)

    assert sufficiency["ready"] is True
    assert sufficiency["blocking_reasons"] == []
    assert sufficiency["accepted_labels"] == ["severe", "benign"]
    assert sufficiency["label_counts"] == {"severe": 3, "benign": 7}


def test_calibration_summary_builds_with_corpus_sufficiency_snapshot_for_expanded_corpus() -> None:
    thresholds = load_thresholds()
    scorer = FastScorer(thresholds)
    corpus = load_calibration_corpus(CORPUS)

    summary = build_calibration_summary(corpus, scorer=scorer, thresholds=thresholds, repo_root=REPO_ROOT)

    assert summary["summary_version"] == "local-analyzer-calibration-summary.v1"
    assert summary["feature_set_version"] == "fast-scorer-baseline-features.v1"
    assert summary["analyzer_version"] == "fast-scorer-2026-04-19"
    assert summary["runner_version"] == "warning-agent-trust-benchmark-runner.v1"
    assert summary["total_cases"] == 30
    assert summary["severe_case_count"] == 8
    assert summary["sample_limited"] is False
    assert summary["gate_ready"] is True
    assert summary["threshold_snapshot"]["confidence_threshold"] == 0.55
    assert summary["corpus_sufficiency"]["ready"] is True
    assert summary["corpus_sufficiency"]["accepted_labels"] == ["severe", "benign"]
    assert summary["corpus_sufficiency"]["label_counts"] == {"severe": 8, "benign": 22}
    assert summary["corpus_sufficiency"]["blocking_reasons"] == []
    assert summary["severe_recall"] >= 0.85
    assert summary["investigation_precision"] >= 0.6
    assert summary["investigation_candidate_rate"] <= 0.35
    assert summary["notes"] == []
