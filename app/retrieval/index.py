"""SQLite FTS5 retrieval index for warning-agent artifacts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.contracts_common import DATA_DIR


class RetrievalIndex:
    def __init__(self, db_path: Path = DATA_DIR / "retrieval" / "retrieval.sqlite3") -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS retrieval_docs USING fts5(
                    doc_id UNINDEXED,
                    kind UNINDEXED,
                    service,
                    operation,
                    body
                )
                """
            )
            connection.commit()

    def upsert_document(
        self,
        *,
        doc_id: str,
        kind: str,
        service: str,
        operation: str | None,
        body: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM retrieval_docs WHERE doc_id = ?", (doc_id,))
            connection.execute(
                "INSERT INTO retrieval_docs (doc_id, kind, service, operation, body) VALUES (?, ?, ?, ?, ?)",
                (doc_id, kind, service, operation or "", body),
            )
            connection.commit()

    def search(
        self,
        query: str,
        *,
        service: str | None = None,
        limit: int = 5,
        include_body: bool = False,
    ) -> list[dict[str, str | float]]:
        select_fields = "doc_id, kind, service, operation, bm25(retrieval_docs) AS score"
        if include_body:
            select_fields += ", body"
        sql = f"SELECT {select_fields} FROM retrieval_docs WHERE retrieval_docs MATCH ?"
        params: list[str | int] = [query]
        if service:
            sql += " AND service = ?"
            params.append(service)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
