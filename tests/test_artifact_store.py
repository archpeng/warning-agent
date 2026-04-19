from __future__ import annotations

from pathlib import Path

from app.storage.artifact_store import JSONLArtifactStore


def test_jsonl_artifact_store_appends_and_reads_records(tmp_path: Path) -> None:
    store = JSONLArtifactStore(root=tmp_path)

    store.append("packets", {"packet_id": "ipk_demo_1"})
    store.append("packets", {"packet_id": "ipk_demo_2"})

    records = store.read_all("packets")

    assert [record["packet_id"] for record in records] == ["ipk_demo_1", "ipk_demo_2"]
    assert store.artifact_path("packets").name == "packets.jsonl"
