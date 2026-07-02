from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Publication:
    id: int | None = None
    title: str = ""
    year: int | None = None
    venue: str = ""
    publication_type: str = "other"
    raw_text: str = ""
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    openalex_id: str | None = None
    match_status: str = "unmatched"


@dataclass(slots=True)
class CitationSnapshot:
    publication_id: int
    captured_at: str
    citation_count: int
    citing_openalex_ids: list[str]


@dataclass(slots=True)
class ValidationResult:
    citation: str
    status: str
    publication_id: int | None = None
    publication_title: str | None = None
    diffs: dict[str, dict[str, Any]] = field(default_factory=dict)
