from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from citewatch.models import Publication


class Store:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    year INTEGER,
                    venue TEXT,
                    publication_type TEXT,
                    raw_text TEXT,
                    authors_json TEXT,
                    doi TEXT,
                    openalex_id TEXT,
                    match_status TEXT DEFAULT 'unmatched'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS citation_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publication_id INTEGER NOT NULL,
                    captured_at TEXT NOT NULL,
                    citation_count INTEGER NOT NULL,
                    citing_openalex_ids_json TEXT NOT NULL,
                    FOREIGN KEY(publication_id) REFERENCES publications(id)
                )
                """
            )

    def add_publications(self, publications: list[Publication]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO publications
                (
                    title,
                    year,
                    venue,
                    publication_type,
                    raw_text,
                    authors_json,
                    doi,
                    openalex_id,
                    match_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        p.title,
                        p.year,
                        p.venue,
                        p.publication_type,
                        p.raw_text,
                        json.dumps(p.authors),
                        p.doi,
                        p.openalex_id,
                        p.match_status,
                    )
                    for p in publications
                ],
            )

    def list_publications(self) -> list[Publication]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM publications ORDER BY id").fetchall()
        return [
            Publication(
                id=row["id"],
                title=row["title"],
                year=row["year"],
                venue=row["venue"] or "",
                publication_type=row["publication_type"] or "other",
                raw_text=row["raw_text"] or "",
                authors=json.loads(row["authors_json"] or "[]"),
                doi=row["doi"],
                openalex_id=row["openalex_id"],
                match_status=row["match_status"] or "unmatched",
            )
            for row in rows
        ]

    def update_match(
        self,
        publication_id: int,
        doi: str | None,
        openalex_id: str | None,
        status: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE publications SET doi = ?, openalex_id = ?, match_status = ? WHERE id = ?",
                (doi, openalex_id, status, publication_id),
            )

    def add_snapshot(
        self,
        publication_id: int,
        captured_at: str,
        citation_count: int,
        citing_ids: list[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO citation_snapshots (
                    publication_id,
                    captured_at,
                    citation_count,
                    citing_openalex_ids_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (publication_id, captured_at, citation_count, json.dumps(citing_ids)),
            )

    def get_by_doi(self, doi: str) -> Publication | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM publications WHERE doi = ?",
                (doi,),
            ).fetchone()
        if not row:
            return None
        return Publication(
            id=row["id"],
            title=row["title"],
            year=row["year"],
            venue=row["venue"] or "",
            publication_type=row["publication_type"] or "other",
            raw_text=row["raw_text"] or "",
            authors=json.loads(row["authors_json"] or "[]"),
            doi=row["doi"],
            openalex_id=row["openalex_id"],
            match_status=row["match_status"] or "unmatched",
        )

    def latest_snapshot(self, publication_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM citation_snapshots
                WHERE publication_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (publication_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "publication_id": row["publication_id"],
            "captured_at": row["captured_at"],
            "citation_count": row["citation_count"],
            "citing_openalex_ids": json.loads(row["citing_openalex_ids_json"]),
        }

    def previous_snapshot(self, publication_id: int) -> dict | None:
        """Return the second-most-recent snapshot for *publication_id*, or ``None``."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM citation_snapshots
                WHERE publication_id = ?
                ORDER BY id DESC
                LIMIT 1 OFFSET 1
                """,
                (publication_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "publication_id": row["publication_id"],
            "captured_at": row["captured_at"],
            "citation_count": row["citation_count"],
            "citing_openalex_ids": json.loads(row["citing_openalex_ids_json"]),
        }
