"""Replay + landed outcome corpus assembly helpers for warning-agent W4."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, TypedDict

from app.analyzer.calibrate import load_calibration_corpus
from app.analyzer.contracts import KnownOutcome, RetrievalHit
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.storage.artifact_store import JSONLArtifactStore

FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION: Final = "feedback-compare-corpus.v1"
DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH: Final = Path("data/feedback/feedback-compare-corpus.json")

CompareCaseSource = Literal["replay_baseline", "landed_outcome"]


class CompareInputRefs(TypedDict):
    packet_id: str
    decision_id: str
    investigation_id: str | None
    report_id: str | None
    outcome_id: str | None
    replay_case_id: str | None


class FeedbackCompareCase(TypedDict):
    case_id: str
    case_source: CompareCaseSource
    label: KnownOutcome
    packet: dict[str, object]
    retrieval_hits: list[RetrievalHit]
    input_refs: CompareInputRefs


class FeedbackCompareCorpusContract(TypedDict):
    replay_case_count: int
    landed_outcome_case_count: int
    unknown_outcome_skipped_count: int
    total_cases: int


class FeedbackCompareCorpus(TypedDict):
    schema_version: str
    generated_at: str
    corpus_contract: FeedbackCompareCorpusContract
    cases: list[FeedbackCompareCase]


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _record_by_id(records: list[dict], *, id_field: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for record in records:
        indexed[str(record[id_field])] = record
    return indexed


def assemble_feedback_compare_corpus(
    *,
    artifact_store: JSONLArtifactStore,
    output_path: str | Path = DEFAULT_FEEDBACK_COMPARE_CORPUS_PATH,
    calibration_corpus_path: str | Path = Path("fixtures/evidence/local-analyzer-calibration-corpus.json"),
    repo_root: Path = Path("."),
) -> FeedbackCompareCorpus:
    repo_root = Path(repo_root)
    cases: list[FeedbackCompareCase] = []

    replay_corpus = load_calibration_corpus(repo_root / calibration_corpus_path)
    for replay_case in replay_corpus:
        replay = load_manual_replay_fixture(repo_root / replay_case["replay_fixture"])
        evidence = _read_json(repo_root / replay_case["evidence_fixture"])
        packet = build_incident_packet_from_bundle(
            normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay"),
            evidence,
        )
        cases.append(
            {
                "case_id": f"replay::{replay_case['case_id']}",
                "case_source": "replay_baseline",
                "label": replay_case["label"],
                "packet": packet,
                "retrieval_hits": replay_case["retrieval_hits"],
                "input_refs": {
                    "packet_id": str(packet["packet_id"]),
                    "decision_id": "",
                    "investigation_id": None,
                    "report_id": None,
                    "outcome_id": None,
                    "replay_case_id": replay_case["case_id"],
                },
            }
        )

    packets = _record_by_id(artifact_store.read_all("packets"), id_field="packet_id")
    decisions = _record_by_id(artifact_store.read_all("decisions"), id_field="decision_id")
    unknown_outcome_skipped_count = 0

    for outcome in artifact_store.read_all("outcomes"):
        label = str(outcome["summary"]["known_outcome"])
        if label == "unknown":
            unknown_outcome_skipped_count += 1
            continue

        packet_id = str(outcome["input_refs"]["packet_id"])
        decision_id = str(outcome["input_refs"]["decision_id"])
        if packet_id not in packets:
            raise ValueError(f"missing packet artifact for landed outcome: {packet_id}")
        if decision_id not in decisions:
            raise ValueError(f"missing decision artifact for landed outcome: {decision_id}")

        cases.append(
            {
                "case_id": f"outcome::{outcome['outcome_id']}",
                "case_source": "landed_outcome",
                "label": label,
                "packet": packets[packet_id],
                "retrieval_hits": list(decisions[decision_id].get("retrieval_hits", [])),
                "input_refs": {
                    "packet_id": packet_id,
                    "decision_id": decision_id,
                    "investigation_id": outcome["input_refs"].get("investigation_id"),
                    "report_id": outcome["input_refs"].get("report_id"),
                    "outcome_id": str(outcome["outcome_id"]),
                    "replay_case_id": None,
                },
            }
        )

    replay_case_count = sum(1 for case in cases if case["case_source"] == "replay_baseline")
    landed_outcome_case_count = sum(1 for case in cases if case["case_source"] == "landed_outcome")
    corpus: FeedbackCompareCorpus = {
        "schema_version": FEEDBACK_COMPARE_CORPUS_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "corpus_contract": {
            "replay_case_count": replay_case_count,
            "landed_outcome_case_count": landed_outcome_case_count,
            "unknown_outcome_skipped_count": unknown_outcome_skipped_count,
            "total_cases": len(cases),
        },
        "cases": cases,
    }

    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return corpus
