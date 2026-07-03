from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from citewatch.models import Publication


def _parse_crossref_item(item: dict[str, Any]) -> Publication:
    """Parse a Crossref work item (from /works/{doi} ``message`` field) into a Publication."""
    title = (item.get("title") or [""])[0]
    year: int | None = None
    issued = (item.get("issued") or {}).get("date-parts")
    if issued and issued[0]:
        year = issued[0][0]
    venue = (item.get("container-title") or [""])[0]
    raw_type = item.get("type", "other")
    if "journal" in raw_type:
        pub_type = "article"
    elif "book-chapter" in raw_type:
        pub_type = "chapter"
    elif "book" in raw_type:
        pub_type = "book"
    else:
        pub_type = "other"
    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in (item.get("author") or [])
    ]
    doi = item.get("DOI")
    return Publication(
        title=title,
        year=year,
        venue=venue,
        publication_type=pub_type,
        raw_text="",
        authors=authors,
        doi=doi,
        match_status="matched" if doi else "unmatched",
    )


def _parse_openalex_item(item: dict[str, Any]) -> Publication:
    """Parse an OpenAlex work object into a Publication."""
    title = item.get("display_name", "")
    year: int | None = item.get("publication_year")
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name", "")
    pub_type = item.get("type", "other")
    authors = [
        a["author"]["display_name"]
        for a in (item.get("authorships") or [])
        if (a.get("author") or {}).get("display_name")
    ]
    doi_url = item.get("doi", "") or ""
    doi = doi_url.replace("https://doi.org/", "") if doi_url else None
    openalex_id = item.get("id")
    return Publication(
        title=title,
        year=year,
        venue=venue,
        publication_type=pub_type,
        raw_text="",
        authors=authors,
        doi=doi,
        openalex_id=openalex_id,
        match_status="matched" if (doi or openalex_id) else "unmatched",
    )


class DoiFetcher:
    """Fetch canonical publication metadata by DOI via Crossref (with OpenAlex fallback)."""

    def __init__(
        self,
        contact_email: str = "citewatch@example.com",
        timeout: float = 15.0,
        sleeper: Callable[[], None] | None = None,
    ) -> None:
        self.timeout = timeout
        self.sleeper = sleeper or (lambda: time.sleep(0.2))
        self.headers = {"User-Agent": f"citewatch/0.1 ({contact_email})"}

    def _get_json(self, url: str) -> dict[str, Any]:
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        self.sleeper()
        return response.json()

    def fetch(self, doi: str) -> Publication | None:
        """Return a Publication for *doi*, or ``None`` if unresolvable."""
        pub: Publication | None = None

        # Primary: Crossref direct DOI lookup
        try:
            data = self._get_json(f"https://api.crossref.org/works/{doi}")
            item = data.get("message") or {}
            if item:
                pub = _parse_crossref_item(item)
        except Exception:
            pass

        # Enrich / fallback: OpenAlex DOI lookup
        try:
            oa = self._get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
            if pub is None:
                pub = _parse_openalex_item(oa)
            else:
                # Enrich Crossref result with OpenAlex ID
                pub.openalex_id = oa.get("id")
                if pub.openalex_id:
                    pub.match_status = "matched"
        except Exception:
            pass

        return pub
