from __future__ import annotations

import re

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from citewatch.models import Publication, ValidationResult
from citewatch.store import Store

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
TITLE_RE = re.compile(r"[\"“](.*?)[\"”]")


def _normalize_title(value: str) -> str:
    return re.sub(r"[^\w\s]", "", value).lower().strip()


def _best_match(citation: str, publications: list[Publication]) -> tuple[Publication | None, int]:
    best = None
    best_score = -1
    for pub in publications:
        score = fuzz.token_set_ratio(citation, pub.title)
        if score > best_score:
            best_score = score
            best = pub
    return best, best_score


def validate_citation(citation: str, store: Store, min_score: int = 60) -> ValidationResult:
    publications = store.list_publications()
    if not publications:
        return ValidationResult(citation=citation, status="not-found")

    pub, score = _best_match(citation, publications)
    if not pub or score < min_score:
        return ValidationResult(citation=citation, status="not-found")

    diffs: dict[str, dict[str, str | int | None]] = {}

    title_text = TITLE_RE.search(citation)
    actual_title = title_text.group(1).strip() if title_text else citation
    title_score = Levenshtein.normalized_similarity(
        _normalize_title(actual_title),
        _normalize_title(pub.title),
    )
    if title_score < 0.995:
        diffs["title"] = {"expected": pub.title, "actual": actual_title}

    year_match = YEAR_RE.search(citation)
    actual_year = int(year_match.group(1)) if year_match else None
    if pub.year and actual_year != pub.year:
        diffs["year"] = {"expected": pub.year, "actual": actual_year}

    if pub.venue and pub.venue.lower() not in citation.lower():
        diffs["venue"] = {"expected": pub.venue, "actual": citation}

    if pub.authors:
        primary_last_name = pub.authors[0].split()[-1]
        if primary_last_name.lower() not in citation.lower():
            diffs["author"] = {"expected": pub.authors[0], "actual": citation}

    status = "mismatch" if diffs else "ok"
    return ValidationResult(
        citation=citation,
        status=status,
        publication_id=pub.id,
        publication_title=pub.title,
        diffs=diffs,
    )


def validate_many(citations: list[str], store: Store) -> list[ValidationResult]:
    return [validate_citation(citation, store) for citation in citations if citation.strip()]
