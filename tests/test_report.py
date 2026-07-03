from __future__ import annotations

from citewatch.models import Publication
from citewatch.report import render_report
from citewatch.store import Store


def _seed_store(store: Store) -> None:
    store.add_publications(
        [
            Publication(
                title=(
                    "\u201cI Dwell in Possibility\u201d: The Poetics of Space in the Works of "
                    "1980s Japanese Avant-Garde Fashion Designers"
                ),
                year=2024,
                venue="Comparative Literature: East & West",
                publication_type="article",
                authors=["Vivien Jiaqian Zhu"],
                doi="10.1080/25723618.2024.2433301",
                openalex_id="https://openalex.org/W4408934567",
                match_status="matched",
            )
        ]
    )


def test_report_generates_html(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite3")
    _seed_store(store)
    html = render_report(store)
    assert "<!DOCTYPE html>" in html
    assert "citewatch" in html.lower()
    assert "Comparative Literature" in html
    assert "Vivien Jiaqian Zhu" in html
    assert "10.1080/25723618.2024.2433301" in html


def test_report_shows_citation_count(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite3")
    _seed_store(store)
    pubs = store.list_publications()
    pub = pubs[0]
    # Snapshot with some citing works
    store.add_snapshot(pub.id, "2025-01-01T00:00:00Z", 3, ["W1", "W2", "W3"])
    html = render_report(store)
    assert "3 citations" in html
    assert "W1" in html
    assert "W2" in html


def test_report_new_since_snapshot(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite3")
    _seed_store(store)
    pubs = store.list_publications()
    pub = pubs[0]
    # Two snapshots: first has W1+W2, second adds W3
    store.add_snapshot(pub.id, "2025-01-01T00:00:00Z", 2, ["W1", "W2"])
    store.add_snapshot(pub.id, "2025-02-01T00:00:00Z", 3, ["W1", "W2", "W3"])
    html = render_report(store)
    assert "New since last snapshot" in html
    assert "W3" in html


def test_report_empty_db(tmp_path) -> None:
    store = Store(tmp_path / "empty.sqlite3")
    html = render_report(store)
    assert "<!DOCTYPE html>" in html
    assert "No publications" in html


def test_report_command_writes_file(tmp_path, monkeypatch) -> None:
    from citewatch.cli import build_parser

    db = tmp_path / "db.sqlite3"
    store = Store(str(db))
    _seed_store(store)

    out_file = tmp_path / "report.html"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "report", "--out", str(out_file)])
    rc = args.func(args)

    assert rc == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
