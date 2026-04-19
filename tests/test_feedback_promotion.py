from __future__ import annotations

import json
from pathlib import Path

from app.feedback.compare import run_feedback_retrain_compare
from app.feedback.corpus import assemble_feedback_compare_corpus
from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.promotion import run_feedback_promotion_review
from app.runtime_entry import RuntimeEntrypoint, build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"


def test_run_feedback_promotion_review_writes_hold_decision_and_report(tmp_path: Path) -> None:
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
    decision_path = tmp_path / "local-analyzer-promotion-decision.json"
    report_path = tmp_path / "local-analyzer-promotion-report.md"
    assemble_feedback_compare_corpus(
        artifact_store=artifact_store,
        output_path=corpus_path,
        repo_root=REPO_ROOT,
    )
    run_feedback_retrain_compare(
        corpus_path=corpus_path,
        summary_output_path=summary_path,
        candidate_artifact_output_path=candidate_path,
        repo_root=REPO_ROOT,
    )

    decision, report = run_feedback_promotion_review(
        compare_summary_path=summary_path,
        decision_output_path=decision_path,
        report_output_path=report_path,
        repo_root=REPO_ROOT,
    )
    written_decision = json.loads(decision_path.read_text(encoding="utf-8"))

    assert decision == written_decision
    assert decision["final_decision"] == "hold_current"
    assert "landed_outcome_cases_below_promotion_minimum" in decision["rationale"]
    assert "# warning-agent local analyzer promotion review" in report
    assert "final decision: `hold_current`" in report
