from __future__ import annotations

from pathlib import Path

from app.storage.sqlite_store import MetadataStore


def test_metadata_store_initializes_and_lists_records(tmp_path: Path) -> None:
    store = MetadataStore(db_path=tmp_path / "metadata.sqlite3")
    store.initialize()
    store.record_artifact(
        "packets",
        artifact_id="ipk_demo_1",
        schema_version="incident-packet.v1",
        artifact_path="data/packets/packets.jsonl",
        service="checkout",
        operation="POST /api/pay",
        created_at="2026-04-18T12:00:08Z",
    )

    records = store.list_artifacts("packets")

    assert records == [
        {
            "artifact_id": "ipk_demo_1",
            "schema_version": "incident-packet.v1",
            "service": "checkout",
            "operation": "POST /api/pay",
            "created_at": "2026-04-18T12:00:08Z",
            "artifact_path": "data/packets/packets.jsonl",
        }
    ]
