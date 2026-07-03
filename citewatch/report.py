from __future__ import annotations

from citewatch.store import Store

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Georgia, serif; background: #fafaf8; color: #1a1a1a; padding: 2rem; }
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
h2 {
  font-size: 1.3rem; margin: 1.5rem 0 0.5rem;
  border-bottom: 1px solid #ccc; padding-bottom: 0.3rem;
}
h3 { font-size: 1.1rem; margin: 1rem 0 0.3rem; }
.meta { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
.pub {
  background: #fff; border: 1px solid #ddd; border-radius: 4px;
  padding: 1rem; margin-bottom: 1rem;
}
.pub-title { font-weight: bold; font-size: 1rem; }
.pub-meta { color: #555; font-size: 0.85rem; margin-top: 0.25rem; }
.badge {
  display: inline-block; background: #e8f4f8; color: #0066aa;
  border-radius: 3px; padding: 0.1rem 0.4rem; font-size: 0.8rem; margin-left: 0.5rem;
}
.badge-new { background: #fff3cd; color: #856404; }
.citing-list { margin-top: 0.5rem; padding-left: 1.2rem; font-size: 0.85rem; color: #333; }
.citing-list li { margin-bottom: 0.2rem; }
.new-section {
  background: #fffbea; border: 1px solid #f0d060;
  border-radius: 4px; padding: 1rem; margin-bottom: 1rem;
}
.empty { color: #888; font-style: italic; }
a { color: #0066aa; text-decoration: none; }
a:hover { text-decoration: underline; }
"""

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>citewatch report</title>
<style>{css}</style>
</head>
<body>
<h1>citewatch — Citation Report</h1>
<p class="meta">Generated: {generated}</p>
{body}
</body>
</html>
"""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_report(store: Store) -> str:
    """Render a self-contained HTML citation report from *store*."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    publications = store.list_publications()
    sections: list[str] = []

    # ── New-since-last-snapshot section ─────────────────────────────────────
    new_entries: list[str] = []
    for pub in publications:
        if pub.id is None:
            continue
        snap = store.latest_snapshot(pub.id)
        prev = store.previous_snapshot(pub.id)
        if snap and prev:
            prev_ids = set(prev["citing_openalex_ids"])
            new_ids = [x for x in snap["citing_openalex_ids"] if x not in prev_ids]
            if new_ids:
                oa_links = "".join(
                    f'<li><a href="{_escape(oid)}">{_escape(oid)}</a></li>'
                    for oid in new_ids
                )
                new_entries.append(
                    f"<div class='pub-title'>{_escape(pub.title)}</div>"
                    f"<ul class='citing-list'>{oa_links}</ul>"
                )

    if new_entries:
        inner = "".join(
            f"<div class='pub' style='margin-bottom:0.5rem'>{e}</div>"
            for e in new_entries
        )
        count_badge = f"<span class='badge badge-new'>{len(new_entries)} publication(s)</span>"
        sections.append(
            f"<h2>New since last snapshot {count_badge}</h2>"
            f"<div class='new-section'>{inner}</div>"
        )
    else:
        sections.append(
            "<h2>New since last snapshot</h2>"
            "<p class='empty'>No new citing works detected since the previous snapshot.</p>"
        )

    # ── Publication list ─────────────────────────────────────────────────────
    sections.append(f"<h2>Publications ({len(publications)})</h2>")
    if not publications:
        sections.append("<p class='empty'>No publications in database.</p>")
    else:
        for pub in publications:
            snap = store.latest_snapshot(pub.id) if pub.id is not None else None
            count = snap["citation_count"] if snap else 0
            citing_ids = snap["citing_openalex_ids"] if snap else []

            doi_link = ""
            if pub.doi:
                doi_url = f"https://doi.org/{pub.doi}"
                doi_link = f' <a href="{_escape(doi_url)}">{_escape(pub.doi)}</a>'

            authors_str = ", ".join(pub.authors) if pub.authors else ""
            year_str = str(pub.year) if pub.year else "n.d."
            venue_str = f" <em>{_escape(pub.venue)}</em>." if pub.venue else ""

            citing_html = ""
            if citing_ids:
                items = "".join(
                    f'<li><a href="{_escape(oid)}">{_escape(oid)}</a></li>'
                    for oid in citing_ids
                )
                citing_html = f"<ul class='citing-list'>{items}</ul>"

            sections.append(
                f"<div class='pub'>"
                f"<div class='pub-title'>{_escape(pub.title)}"
                f"<span class='badge'>{count} citation{'s' if count != 1 else ''}</span></div>"
                f"<div class='pub-meta'>"
                f"{_escape(authors_str)} ({year_str}).{venue_str}{doi_link}"
                f"</div>"
                f"{citing_html}"
                f"</div>"
            )

    body = "\n".join(sections)
    return _HTML_TEMPLATE.format(css=_CSS, generated=_escape(now), body=body)
