"""Benchmark helpers for W3 routing + handoff quality evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal, TypedDict

from app.analyzer.base import load_thresholds
from app.analyzer.runtime import resolve_runtime_scorer
from app.investigator.runtime import run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture

LOCAL_HANDOFF_EVAL_CORPUS_SCHEMA_VERSION: Final = "local-handoff-eval-corpus.v1"
LOCAL_HANDOFF_MIN_CASES: Final = 12

HandoffTarget = Literal["none", "local_primary", "cloud_fallback"]


class HandoffBenchmarkCase(TypedDict):
    case_id: str
    replay_fixture: str
    evidence_fixture: str
    expected_handoff_target: HandoffTarget
    expected_reason_codes: list[str]


class HandoffCorpusContract(TypedDict):
    schema_version: str | None
    minimum_cases: int
    measurement_ready: bool
    blocking_reasons: list[str]


def load_local_handoff_corpus(path: str | Path) -> list[HandoffBenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != LOCAL_HANDOFF_EVAL_CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported handoff corpus schema_version '{payload.get('schema_version')}'"
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("handoff eval corpus must contain non-empty cases")
    return cases


def evaluate_local_handoff_corpus_contract(cases: list[HandoffBenchmarkCase]) -> HandoffCorpusContract:
    blockers: list[str] = []
    if len(cases) < LOCAL_HANDOFF_MIN_CASES:
        blockers.append("handoff_eval_cases_below_w3_minimum")
    return {
        "schema_version": LOCAL_HANDOFF_EVAL_CORPUS_SCHEMA_VERSION,
        "minimum_cases": LOCAL_HANDOFF_MIN_CASES,
        "measurement_ready": not blockers,
        "blocking_reasons": blockers,
    }


def run_local_handoff_benchmark(
    *,
    corpus_path: str | Path,
    repo_root: Path = Path("."),
) -> dict[str, object]:
    cases = load_local_handoff_corpus(corpus_path)
    corpus_contract = evaluate_local_handoff_corpus_contract(cases)
    scorer = resolve_runtime_scorer(
        repo_root=repo_root,
        thresholds=load_thresholds(repo_root / "configs" / "thresholds.yaml"),
    )

    expected_cloud = 0
    actual_cloud = 0
    target_alignment = 0
    reason_alignment = 0

    for case in cases:
        replay = load_manual_replay_fixture(repo_root / case["replay_fixture"])
        normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
        evidence_bundle = json.loads((repo_root / case["evidence_fixture"]).read_text(encoding="utf-8"))
        packet = build_incident_packet_from_bundle(normalized, evidence_bundle)
        decision = scorer.score_packet(packet, retrieval_hits=[])
        execution = run_investigation_runtime(
            packet,
            decision,
            config_path=repo_root / "configs" / "escalation.yaml",
            repo_root=repo_root,
        )

        actual_target: HandoffTarget
        if execution.final_result is None:
            actual_target = "none"
        elif execution.final_result["investigator_tier"] == "cloud_fallback_investigator":
            actual_target = "cloud_fallback"
        else:
            actual_target = "local_primary"

        expected_target = case["expected_handoff_target"]
        expected_cloud += int(expected_target == "cloud_fallback")
        actual_cloud += int(actual_target == "cloud_fallback")
        target_alignment += int(actual_target == expected_target)

        actual_reason_codes = (
            execution.local_result["summary"]["reason_codes"]
            if execution.local_result is not None
            else decision["reason_codes"]
        )
        expected_reason_codes = case["expected_reason_codes"]
        reason_alignment += int(list(actual_reason_codes[: len(expected_reason_codes)]) == expected_reason_codes)

    total_cases = len(cases)
    measurement_ready = corpus_contract["measurement_ready"]
    metrics = {
        "total_cases": total_cases,
        "expected_cloud_fallback_case_count": expected_cloud,
        "actual_cloud_fallback_case_count": actual_cloud,
        "handoff_target_alignment_rate": round(target_alignment / total_cases, 2) if total_cases else 0.0,
        "carry_reason_code_alignment_rate": round(reason_alignment / total_cases, 2) if total_cases else 0.0,
    }
    acceptance = {
        "accepted": bool(
            measurement_ready
            and metrics["handoff_target_alignment_rate"] == 1.0
            and metrics["carry_reason_code_alignment_rate"] == 1.0
        ),
        "blockers": [
            *([] if measurement_ready else ["benchmark_measurement_not_ready"]),
            *([] if metrics["handoff_target_alignment_rate"] == 1.0 else ["handoff_target_alignment_below_gate"]),
            *([] if metrics["carry_reason_code_alignment_rate"] == 1.0 else ["handoff_reason_alignment_below_gate"]),
        ],
        "checks": {
            "benchmark_measurement_ready": {
                "actual": measurement_ready,
                "expected": True,
                "comparator": "==",
                "passed": measurement_ready,
            },
            "handoff_target_alignment_rate": {
                "actual": metrics["handoff_target_alignment_rate"],
                "expected": 1.0,
                "comparator": "==",
                "passed": metrics["handoff_target_alignment_rate"] == 1.0,
            },
            "carry_reason_code_alignment_rate": {
                "actual": metrics["carry_reason_code_alignment_rate"],
                "expected": 1.0,
                "comparator": "==",
                "passed": metrics["carry_reason_code_alignment_rate"] == 1.0,
            },
        },
    }

    return {
        "analyzer_version": scorer.analyzer_version,
        "corpus_contract": corpus_contract,
        "metrics": metrics,
        "acceptance": acceptance,
        "notes": [
            "trained scorer handoff benchmark reflects actual runtime target alignment and carried reason-code alignment"
        ],
    }
