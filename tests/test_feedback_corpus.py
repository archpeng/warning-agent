from __future__ import annotations

import json
from pathlib import Path

from app.feedback.corpus import assemble_feedback_compare_corpus
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.runtime_entry import RuntimeEntrypoint, build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


def test_assemble_feedback_compare_corpus_combines_replay_and_landed_outcomes(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    execution = execute_runtime_entrypoint(
        RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE),
        repo_root=REPO_ROOT,
        artifact_store=artifact_store,
    )
    summary = build_runtime_execution_summary(execution)
    ingest_incident_outcome(
        OutcomeIngestRequest(
            source="operator",
            recorded_at="2026-04-19T09:00:00Z",
            service=str(execution.packet["service"]),
            operation=str(execution.packet.get("operation") or ""),
            environment=str(execution.packet["environment"]),
            packet_id=summary.packet_id,
            decision_id=summary.decision_id,
            investigation_id=summary.investigation_id,
            report_id=summary.report_id,
            known_outcome="severe",
            final_severity_band=str(execution.decision["severity_band"]),
            final_recommended_action=str(execution.decision["recommended_action"]),
            resolution_summary="operator confirmed the incident and closed it after rollback",
            notes=("used rollback as mitigation",),
        ),
        artifact_store=artifact_store,
    )
    output_path = tmp_path / "feedback-compare-corpus.json"

    corpus = assemble_feedback_compare_corpus(
        artifact_store=artifact_store,
        output_path=output_path,
        repo_root=REPO_ROOT,
    )
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert corpus == written
    assert corpus["schema_version"] == "feedback-compare-corpus.v1"
    assert corpus["corpus_contract"]["replay_case_count"] == 30
    assert corpus["corpus_contract"]["landed_outcome_case_count"] == 1
    assert corpus["corpus_contract"]["unknown_outcome_skipped_count"] == 0
    assert corpus["corpus_contract"]["total_cases"] == 31
    landed_cases = [case for case in corpus["cases"] if case["case_source"] == "landed_outcome"]
    assert len(landed_cases) == 1
    assert landed_cases[0]["label"] == "severe"
    assert landed_cases[0]["input_refs"]["outcome_id"] == "out_operator_checkout_post_api_pay_20260419t090000z"
    assert landed_cases[0]["retrieval_hits"] == execution.decision["retrieval_hits"]
