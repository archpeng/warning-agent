"""SQLite metadata index for warning-agent artifacts."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Final, Literal

from app.contracts_common import DATA_DIR

ArtifactTable = Literal[
    "packets",
    "local_decisions",
    "investigations",
    "alert_reports",
    "outcomes",
]

TABLES: Final[tuple[ArtifactTable, ...]] = (
    "packets",
    "local_decisions",
    "investigations",
    "alert_reports",
    "outcomes",
)


class MetadataStore:
    def __init__(self, db_path: Path = DATA_DIR / "metadata.sqlite3") -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            for table in TABLES:
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        artifact_id TEXT PRIMARY KEY,
                        schema_version TEXT NOT NULL,
                        service TEXT,
                        operation TEXT,
                        created_at TEXT,
                        artifact_path TEXT NOT NULL
                    )
                    """
                )
            connection.commit()

    def record_artifact(
        self,
        table: ArtifactTable,
        *,
        artifact_id: str,
        schema_version: str,
        artifact_path: str,
        service: str | None = None,
        operation: str | None = None,
        created_at: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                f"""
                INSERT OR REPLACE INTO {table}
                (artifact_id, schema_version, service, operation, created_at, artifact_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, schema_version, service, operation, created_at, artifact_path),
            )
            connection.commit()

    def list_artifacts(self, table: ArtifactTable) -> list[dict[str, str | None]]:
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT artifact_id, schema_version, service, operation, created_at, artifact_path FROM {table} ORDER BY artifact_id"
            ).fetchall()
        return [dict(row) for row in rows]
