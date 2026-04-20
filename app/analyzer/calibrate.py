"""Calibration and threshold helpers for the local analyzer baseline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Protocol, TypedDict, cast

from app.analyzer.base import AnalyzerFeatures, AnalyzerThresholds, round_score
from app.analyzer.contracts import RetrievalHit
from app.analyzer.corpus_packets import build_manual_replay_packet
from app.analyzer.versioning import FAST_SCORER_FEATURE_SET_VERSION
from app.benchmarks.contracts import build_surface_header

CALIBRATION_CORPUS_SCHEMA_VERSION: Final = "local-analyzer-calibration-corpus.v1"
ACCEPTED_CALIBRATION_LABELS: Final[tuple[str, ...]] = ("severe", "benign")
ACCEPTED_RETRIEVAL_OUTCOMES: Final[frozenset[str]] = frozenset({"severe", "benign", "unknown"})


class LocalAnalyzerProtocol(Protocol):
    def score_packet(self, packet: dict[str, object], *, retrieval_hits: list[RetrievalHit] | None = None) -> dict:
        ...


class CalibrationCase(TypedDict):
    case_id: str
    label: str
    expected_needs_investigation: bool
    replay_fixture: str
    evidence_fixture: str
    retrieval_hits: list[RetrievalHit]


class CorpusSufficiency(TypedDict):
    total_cases: int
    severe_case_count: int
    minimum_calibration_cases: int
    minimum_severe_cases: int
    accepted_labels: list[str]
    label_counts: dict[str, int]
    ready: bool
    blocking_reasons: list[str]


class CalibrationSummary(TypedDict):
    summary_version: str
    feature_set_version: str
    analyzer_version: str
    runner_version: str
    total_cases: int
    severe_case_count: int
    predicted_severe_count: int
    predicted_investigation_count: int
    severe_recall: float
    investigation_precision: float
    investigation_candidate_rate: float
    average_confidence: float
    threshold_snapshot: dict[str, float | int | dict[str, float]]
    corpus_sufficiency: CorpusSufficiency
    sample_limited: bool
    gate_ready: bool
    notes: list[str]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_retrieval_hit(*, case_id: str, hit_index: int, payload: object) -> RetrievalHit:
    _require(isinstance(payload, dict), f"case {case_id} retrieval hit #{hit_index} must be an object")

    packet_id = str(payload.get("packet_id") or "").strip()
    similarity = payload.get("similarity")
    known_outcome = str(payload.get("known_outcome") or "").strip()

    _require(packet_id != "", f"case {case_id} retrieval hit #{hit_index} missing packet_id")
    _require(isinstance(similarity, (int, float)), f"case {case_id} retrieval hit #{hit_index} missing similarity")
    _require(
        known_outcome in ACCEPTED_RETRIEVAL_OUTCOMES,
        f"case {case_id} retrieval hit #{hit_index} unsupported known_outcome '{known_outcome}'",
    )

    return {
        "packet_id": packet_id,
        "similarity": float(similarity),
        "known_outcome": cast(str, known_outcome),
    }


def _validate_calibration_case(*, case_index: int, payload: object, seen_case_ids: set[str]) -> CalibrationCase:
    _require(isinstance(payload, dict), f"calibration case #{case_index} must be an object")

    case_id = str(payload.get("case_id") or "").strip()
    label = str(payload.get("label") or "").strip()
    expected_needs_investigation = payload.get("expected_needs_investigation")
    replay_fixture = str(payload.get("replay_fixture") or "").strip()
    evidence_fixture = str(payload.get("evidence_fixture") or "").strip()
    retrieval_hits_payload = payload.get("retrieval_hits")

    _require(case_id != "", f"calibration case #{case_index} missing case_id")
    _require(case_id not in seen_case_ids, f"duplicate calibration case_id '{case_id}'")
    _require(label in ACCEPTED_CALIBRATION_LABELS, f"case {case_id} has unsupported label '{label}'")
    _require(
        isinstance(expected_needs_investigation, bool),
        f"case {case_id} expected_needs_investigation must be a boolean",
    )
    _require(replay_fixture != "", f"case {case_id} missing replay_fixture")
    _require(evidence_fixture != "", f"case {case_id} missing evidence_fixture")
    _require(isinstance(retrieval_hits_payload, list), f"case {case_id} retrieval_hits must be a list")

    retrieval_hits = [
        _validate_retrieval_hit(case_id=case_id, hit_index=hit_index, payload=hit)
        for hit_index, hit in enumerate(retrieval_hits_payload)
    ]

    seen_case_ids.add(case_id)
    return {
        "case_id": case_id,
        "label": label,
        "expected_needs_investigation": expected_needs_investigation,
        "replay_fixture": replay_fixture,
        "evidence_fixture": evidence_fixture,
        "retrieval_hits": retrieval_hits,
    }


def decide_investigation(
    features: AnalyzerFeatures,
    *,
    novelty_score: float,
    confidence: float,
    recommended_action: str,
    severity_score: float,
    thresholds: AnalyzerThresholds,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if novelty_score >= thresholds.novelty_threshold:
        reasons.append("novelty_high")
    if features.blast_radius_score >= thresholds.blast_radius_threshold:
        reasons.append("blast_radius_high")
    if confidence < thresholds.confidence_threshold:
        reasons.append("confidence_low")
    if features.retrieval_conflict >= 1.0:
        reasons.append("retrieval_conflict")
    if not reasons and (
        severity_score >= thresholds.investigation_threshold
        or recommended_action == "page_owner"
    ):
        reasons.append("severity_high")
    return bool(reasons), reasons


def load_calibration_corpus(path: str | Path) -> list[CalibrationCase]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _require(isinstance(payload, dict), "calibration corpus payload must be an object")
    schema_version = payload.get("schema_version")
    _require(
        schema_version == CALIBRATION_CORPUS_SCHEMA_VERSION,
        f"unsupported calibration corpus schema_version '{schema_version}'",
    )
    cases_payload = payload.get("cases")
    _require(isinstance(cases_payload, list), "calibration corpus cases must be a list")

    seen_case_ids: set[str] = set()
    return [
        _validate_calibration_case(case_index=case_index, payload=case, seen_case_ids=seen_case_ids)
        for case_index, case in enumerate(cases_payload)
    ]


def threshold_snapshot(thresholds: AnalyzerThresholds) -> dict[str, float | int | dict[str, float]]:
    return {
        "severity_thresholds": thresholds.severity_thresholds,
        "novelty_threshold": thresholds.novelty_threshold,
        "investigation_threshold": thresholds.investigation_threshold,
        "confidence_threshold": thresholds.confidence_threshold,
        "blast_radius_threshold": thresholds.blast_radius_threshold,
        "minimum_calibration_cases": thresholds.minimum_calibration_cases,
        "minimum_severe_cases": thresholds.minimum_severe_cases,
    }


def evaluate_corpus_sufficiency(
    corpus: list[CalibrationCase],
    *,
    thresholds: AnalyzerThresholds,
) -> CorpusSufficiency:
    label_counts = {label: 0 for label in ACCEPTED_CALIBRATION_LABELS}
    for case in corpus:
        label_counts[case["label"]] += 1

    total_cases = len(corpus)
    severe_case_count = label_counts["severe"]
    blocking_reasons: list[str] = []
    if total_cases < thresholds.minimum_calibration_cases:
        blocking_reasons.append("total_cases_below_minimum")
    if severe_case_count < thresholds.minimum_severe_cases:
        blocking_reasons.append("severe_cases_below_minimum")

    return {
        "total_cases": total_cases,
        "severe_case_count": severe_case_count,
        "minimum_calibration_cases": thresholds.minimum_calibration_cases,
        "minimum_severe_cases": thresholds.minimum_severe_cases,
        "accepted_labels": list(ACCEPTED_CALIBRATION_LABELS),
        "label_counts": label_counts,
        "ready": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
    }


def build_calibration_summary(
    corpus: list[CalibrationCase],
    *,
    scorer: LocalAnalyzerProtocol,
    thresholds: AnalyzerThresholds,
    repo_root: Path = Path('.'),
) -> CalibrationSummary:
    total_cases = len(corpus)
    predicted_severe_count = 0
    predicted_investigation_count = 0
    severe_true_positives = 0
    investigation_true_positives = 0
    confidence_sum = 0.0
    notes: list[str] = []

    corpus_sufficiency = evaluate_corpus_sufficiency(corpus, thresholds=thresholds)
    severe_case_count = corpus_sufficiency["severe_case_count"]

    for case in corpus:
        packet = build_manual_replay_packet(
            repo_root=repo_root,
            replay_fixture=case["replay_fixture"],
            evidence_fixture=case["evidence_fixture"],
        )
        decision = scorer.score_packet(packet, retrieval_hits=case["retrieval_hits"])

        is_severe = case["label"] == "severe"
        predicted_severe = decision["severity_band"] in {"P1", "P2"}
        predicted_investigation = bool(decision["needs_investigation"])

        predicted_severe_count += int(predicted_severe)
        predicted_investigation_count += int(predicted_investigation)
        severe_true_positives += int(is_severe and predicted_severe)
        investigation_true_positives += int(is_severe and predicted_investigation)
        confidence_sum += float(decision["confidence"])

        if predicted_investigation != case["expected_needs_investigation"]:
            notes.append(
                f"case {case['case_id']} predicted needs_investigation={predicted_investigation} "
                f"but expected {case['expected_needs_investigation']}"
            )

    severe_recall = round_score(severe_true_positives / severe_case_count) if severe_case_count else 0.0
    investigation_precision = (
        round_score(investigation_true_positives / predicted_investigation_count)
        if predicted_investigation_count
        else 0.0
    )
    investigation_candidate_rate = round_score(
        predicted_investigation_count / total_cases if total_cases else 0.0
    )
    average_confidence = round_score(confidence_sum / total_cases if total_cases else 0.0)

    sample_limited = not corpus_sufficiency["ready"]
    if sample_limited:
        notes.append(
            "calibration corpus below minimum size; scaffold-only summary is not sufficient for honest closeout "
            f"(total_cases={total_cases}/{thresholds.minimum_calibration_cases}, "
            f"severe_cases={severe_case_count}/{thresholds.minimum_severe_cases})"
        )

    gate_ready = corpus_sufficiency["ready"]

    return {
        **build_surface_header(
            "local_analyzer_calibration",
            feature_set_version=FAST_SCORER_FEATURE_SET_VERSION,
            analyzer_version=scorer.analyzer_version,
        ),
        "total_cases": total_cases,
        "severe_case_count": severe_case_count,
        "predicted_severe_count": predicted_severe_count,
        "predicted_investigation_count": predicted_investigation_count,
        "severe_recall": severe_recall,
        "investigation_precision": investigation_precision,
        "investigation_candidate_rate": investigation_candidate_rate,
        "average_confidence": average_confidence,
        "threshold_snapshot": threshold_snapshot(thresholds),
        "corpus_sufficiency": corpus_sufficiency,
        "sample_limited": sample_limited,
        "gate_ready": gate_ready,
        "notes": notes,
    }
