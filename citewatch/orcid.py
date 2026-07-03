from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from citewatch.models import Publication


def _orcid_summary_to_publication(summary: dict[str, Any]) -> Publication:
    """Convert an ORCID work-summary dict into a minimal Publication."""
    title_block = summary.get("title") or {}
    title = ((title_block.get("title") or {}).get("value") or "").strip()

    year: int | None = None
    pub_date = summary.get("publication-date") or {}
    year_block = pub_date.get("year") or {}
    year_val = year_block.get("value")
    if year_val:
        try:
            year = int(year_val)
        except ValueError:
            pass

    journal_block = summary.get("journal-title") or {}
    venue = (journal_block.get("value") or "").strip()

    raw_type = summary.get("type", "other") or "other"
    if "journal" in raw_type:
        pub_type = "article"
    elif "conference" in raw_type:
        pub_type = "other"
    elif "book" in raw_type:
        pub_type = "book"
    else:
        pub_type = "other"

    return Publication(
        title=title,
        year=year,
        venue=venue,
        publication_type=pub_type,
        raw_text="",
        authors=[],
    )


class OrcidClient:
    """Thin client for the ORCID public API works endpoint."""

    BASE_URL = "https://pub.orcid.org/v3.0"

    def __init__(
        self,
        contact_email: str = "citewatch@example.com",
        timeout: float = 15.0,
        sleeper: Callable[[], None] | None = None,
    ) -> None:
        self.timeout = timeout
        self.sleeper = sleeper or (lambda: time.sleep(0.2))
        self.headers = {
            "Accept": "application/json",
            "User-Agent": f"citewatch/0.1 ({contact_email})",
        }

    def _get_json(self, url: str) -> dict[str, Any]:
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        self.sleeper()
        return response.json()

    def fetch_works(self, orcid_id: str) -> list[dict[str, Any]]:
        """Return a list of work-entry dicts for the given ORCID iD.

        Each entry contains:
        - ``doi``: str or None
        - ``summary``: the raw ORCID work-summary dict (first in each group)
        """
        data = self._get_json(f"{self.BASE_URL}/{orcid_id}/works")
        entries: list[dict[str, Any]] = []
        for group in data.get("group") or []:
            summaries = group.get("work-summary") or []
            if not summaries:
                continue
            # Use the first summary per group (highest-precedence source)
            summary = summaries[0]
            doi: str | None = None
            ext_ids = (summary.get("external-ids") or {}).get("external-id") or []
            for eid in ext_ids:
                if eid.get("external-id-type") == "doi":
                    doi = eid.get("external-id-value")
                    break
            entries.append({"doi": doi, "summary": summary})
        return entries
