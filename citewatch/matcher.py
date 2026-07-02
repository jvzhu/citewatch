from __future__ import annotations

import time
from typing import Any

import requests
from rapidfuzz import fuzz

from citewatch.models import Publication


class ScholarlyMatcher:
    def __init__(
        self,
        contact_email: str = "citewatch@example.com",
        timeout: float = 15.0,
        min_score: int = 70,
        sleeper: callable | None = None,
    ) -> None:
        self.timeout = timeout
        self.min_score = min_score
        self.sleeper = sleeper or (lambda: time.sleep(0.2))
        self.headers = {"User-Agent": f"citewatch/0.1 ({contact_email})"}

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        self.sleeper()
        return response.json()

    def resolve(self, publication: Publication) -> tuple[str | None, str | None, str]:
        crossref = self._get_json(
            "https://api.crossref.org/works",
            {"query.title": publication.title, "rows": 5},
        )
        best_crossref = None
        best_score = -1
        for item in crossref.get("message", {}).get("items", []):
            title = (item.get("title") or [""])[0]
            score = fuzz.token_set_ratio(publication.title, title)
            if publication.year and item.get("issued", {}).get("date-parts"):
                issued_year = item["issued"]["date-parts"][0][0]
                if abs(issued_year - publication.year) <= 1:
                    score += 10
            if score > best_score:
                best_score = score
                best_crossref = item

        doi = None
        if best_crossref and best_score >= self.min_score:
            doi = best_crossref.get("DOI")

        openalex = self._get_json(
            "https://api.openalex.org/works",
            {"search": publication.title, "per-page": 5},
        )
        best_openalex = None
        best_oa_score = -1
        for item in openalex.get("results", []):
            score = fuzz.token_set_ratio(publication.title, item.get("display_name", ""))
            if publication.year and item.get("publication_year"):
                if abs(item["publication_year"] - publication.year) <= 1:
                    score += 10
            if score > best_oa_score:
                best_oa_score = score
                best_openalex = item

        openalex_id = None
        if best_openalex and best_oa_score >= self.min_score:
            openalex_id = best_openalex.get("id")

        status = "matched" if doi or openalex_id else "unmatched"
        return doi, openalex_id, status
