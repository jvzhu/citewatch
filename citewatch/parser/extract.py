from __future__ import annotations

import re

from citewatch.models import Publication

HEADER_TYPES = {
    "books": "book",
    "articles": "article",
    "chapters": "chapter",
    "edited volumes": "edited volume",
    "translations": "translation",
    "publications": "other",
}

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
TITLE_RE = re.compile(r"[\"“](.*?)[\"”]")


def _infer_title(entry: str) -> str:
    quoted = TITLE_RE.search(entry)
    if quoted:
        return quoted.group(1).strip()
    m = re.match(r"^(?:19\d{2}|20\d{2})\.\s*(.+?)\.", entry)
    if m:
        return m.group(1).strip()
    parts = [p.strip() for p in entry.split(".") if p.strip()]
    return parts[0] if parts else entry.strip()


def extract_publications(text: str) -> list[Publication]:
    lines = [line.strip() for line in text.splitlines()]
    section = "other"
    entries: list[tuple[str, str]] = []
    current: list[str] = []
    current_section = section

    for line in lines:
        if not line:
            continue
        lowered = line.lower().rstrip(":")
        if lowered in HEADER_TYPES:
            if current:
                entries.append((" ".join(current), current_section))
                current = []
            section = HEADER_TYPES[lowered]
            current_section = section
            continue
        if YEAR_RE.match(line) and current:
            entries.append((" ".join(current), current_section))
            current = [line]
            current_section = section
        else:
            current.append(line)

    if current:
        entries.append((" ".join(current), current_section))

    publications: list[Publication] = []
    for entry, entry_section in entries:
        year_match = YEAR_RE.search(entry)
        if not year_match:
            continue
        title = _infer_title(entry)
        publications.append(
            Publication(
                title=title,
                year=int(year_match.group(1)),
                venue="",
                publication_type=entry_section,
                raw_text=entry,
            )
        )

    return publications
