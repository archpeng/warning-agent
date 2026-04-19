"""JSONL artifact storage primitives for warning-agent replay and learning loops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal

from app.contracts_common import DATA_DIR

ArtifactKind = Literal["packets", "decisions", "investigations", "reports", "outcomes", "deliveries"]

ARTIFACT_FILE_NAMES: Final[dict[ArtifactKind, str]] = {
    "packets": "packets.jsonl",
    "decisions": "decisions.jsonl",
    "investigations": "investigations.jsonl",
    "reports": "reports.jsonl",
    "outcomes": "outcomes.jsonl",
    "deliveries": "deliveries.jsonl",
}


class JSONLArtifactStore:
    def __init__(self, root: Path = DATA_DIR) -> None:
        self.root = root

    def _artifact_dir(self, kind: ArtifactKind) -> Path:
        path = self.root / kind
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_path(self, kind: ArtifactKind) -> Path:
        return self._artifact_dir(kind) / ARTIFACT_FILE_NAMES[kind]

    def append(self, kind: ArtifactKind, record: dict) -> Path:
        path = self.artifact_path(kind)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def read_all(self, kind: ArtifactKind) -> list[dict]:
        path = self.artifact_path(kind)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
