from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from citewatch.matcher import ScholarlyMatcher
from citewatch.store import Store


class CitationTracker:
    def __init__(
        self,
        contact_email: str = "citewatch@example.com",
        timeout: float = 15.0,
    ) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": f"citewatch/0.1 ({contact_email})"}

    def _get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_citing_works(self, openalex_id: str) -> tuple[int, list[str]]:
        work = self._get_json(openalex_id)
        cited_by_count = int(work.get("cited_by_count", 0))
        citing_ids: list[str] = []
        cursor = "*"
        while True:
            page = self._get_json(
                "https://api.openalex.org/works",
                {"filter": f"cites:{openalex_id}", "per-page": 200, "cursor": cursor},
            )
            results = page.get("results", [])
            citing_ids.extend([item["id"] for item in results if item.get("id")])
            next_cursor = page.get("meta", {}).get("next_cursor")
            if not next_cursor or not results:
                break
            cursor = next_cursor
        return cited_by_count, citing_ids


def track(
    store: Store,
    matcher: ScholarlyMatcher,
    tracker: CitationTracker,
    diff: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for publication in store.list_publications():
        if not publication.openalex_id:
            doi, openalex_id, status = matcher.resolve(publication)
            store.update_match(publication.id or 0, doi, openalex_id, status)
            publication.doi = doi
            publication.openalex_id = openalex_id
            publication.match_status = status
        if not publication.openalex_id:
            results.append({"publication_id": publication.id, "status": "unmatched"})
            continue

        previous = store.latest_snapshot(publication.id or 0)
        count, citing_ids = tracker.fetch_citing_works(publication.openalex_id)
        store.add_snapshot(publication.id or 0, now, count, citing_ids)
        item: dict[str, Any] = {
            "publication_id": publication.id,
            "status": "tracked",
            "citation_count": count,
        }
        if diff and previous:
            prev_ids = set(previous["citing_openalex_ids"])
            new_ids = [x for x in citing_ids if x not in prev_ids]
            item["new_citations"] = new_ids
        results.append(item)
    return results
