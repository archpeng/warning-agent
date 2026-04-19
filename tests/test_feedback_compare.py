from __future__ import annotations

import json
from pathlib import Path

from app.feedback.compare import run_feedback_retrain_compare
from app.feedback.corpus import assemble_feedback_compare_corpus
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.runtime_entry import RuntimeEntrypoint, build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


def test_run_feedback_retrain_compare_writes_summary_and_candidate_artifact(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    execution = execute_runtime_entrypoint(
        RuntimeEntrypoint(mode="replay", replay_fixture=REPLAY_FIXTURE),
        repo_root=REPO_ROOT,
        artifact_store=artifact_store,
    )
    runtime_summary = build_runtime_execution_summary(execution)
    ingest_incident_outcome(
        OutcomeIngestRequest(
            source="operator",
            recorded_at="2026-04-19T09:00:00Z",
            service=str(execution.packet["service"]),
            operation=str(execution.packet.get("operation") or ""),
            environment=str(execution.packet["environment"]),
            packet_id=runtime_summary.packet_id,
            decision_id=runtime_summary.decision_id,
            investigation_id=runtime_summary.investigation_id,
            report_id=runtime_summary.report_id,
            known_outcome="severe",
            final_severity_band=str(execution.decision["severity_band"]),
            final_recommended_action=str(execution.decision["recommended_action"]),
            resolution_summary="operator confirmed the incident after rollback",
            notes=("rollback applied",),
        ),
        artifact_store=artifact_store,
    )
    corpus_path = tmp_path / "feedback-compare-corpus.json"
    summary_path = tmp_path / "local-analyzer-feedback-compare-summary.json"
    candidate_path = tmp_path / "local-analyzer-trained-scorer.candidate.json"
    assemble_feedback_compare_corpus(
        artifact_store=artifact_store,
        output_path=corpus_path,
        repo_root=REPO_ROOT,
    )

    summary = run_feedback_retrain_compare(
        corpus_path=corpus_path,
        summary_output_path=summary_path,
        candidate_artifact_output_path=candidate_path,
        repo_root=REPO_ROOT,
    )
    written_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    candidate_artifact = json.loads(candidate_path.read_text(encoding="utf-8"))

    assert summary == written_summary
    assert summary["summary_version"] == "local-analyzer-feedback-compare-summary.v1"
    assert summary["corpus_contract"]["total_cases"] == 31
    assert summary["models"]["fast_scorer"]["metrics"]["total_cases"] == 31
    assert summary["models"]["current_runtime"]["metrics"]["total_cases"] == 31
    assert summary["models"]["candidate_retrained"]["metrics"]["total_cases"] == 31
    assert candidate_artifact["artifact_version"] == "local-analyzer-trained-scorer.v1"
    assert candidate_artifact["training_state"] == "ready"
    assert candidate_artifact["weights"] is not None
    assert candidate_artifact["calibration_parameters"] is not None
