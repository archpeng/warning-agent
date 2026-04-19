from __future__ import annotations

from pathlib import Path

from app.feedback.persistence import persist_outcome_record
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


def test_persist_outcome_record_appends_jsonl_and_records_metadata(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)
    outcome = {
        "schema_version": "incident-outcome.v1",
        "outcome_id": "out_checkout_post_pay_20260419t080000z",
        "source": "operator",
        "recorded_at": "2026-04-19T08:00:00Z",
        "service": "checkout",
        "operation": "POST /api/pay",
        "environment": "prod",
        "input_refs": {
            "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
            "decision_id": "lad_checkout_post_pay_20260418t120010z",
            "investigation_id": "inv_checkout_post_pay_20260418t120012z",
            "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
        },
        "summary": {
            "known_outcome": "severe",
            "final_severity_band": "P1",
            "final_recommended_action": "page_owner",
            "resolution_summary": "operator confirmed a real checkout regression and rolled back the change",
        },
        "notes": ["rollback mitigated the incident"],
    }

    persisted = persist_outcome_record(outcome, artifact_store=artifact_store)

    records = artifact_store.read_all("outcomes")
    metadata_store = MetadataStore(db_path=persisted.metadata_db_path)

    assert persisted.artifact_path == artifact_store.artifact_path("outcomes")
    assert [record["outcome_id"] for record in records] == ["out_checkout_post_pay_20260419t080000z"]
    assert metadata_store.list_artifacts("outcomes") == [
        {
            "artifact_id": "out_checkout_post_pay_20260419t080000z",
            "schema_version": "incident-outcome.v1",
            "service": "checkout",
            "operation": "POST /api/pay",
            "created_at": "2026-04-19T08:00:00Z",
            "artifact_path": str(artifact_store.artifact_path("outcomes")),
        }
    ]
