from __future__ import annotations

import json
from pathlib import Path

import pytest

from citewatch.fetcher import DoiFetcher, _parse_crossref_item, _parse_openalex_item
from citewatch.models import Publication
from citewatch.store import Store

FIXTURES = Path(__file__).parent / "fixtures"

ZHU_DOI = "10.1080/25723618.2024.2433301"
ZHU_TITLE = (
    "\u201cI Dwell in Possibility\u201d: The Poetics of Space in the Works of "
    "1980s Japanese Avant-Garde Fashion Designers"
)


@pytest.fixture()
def crossref_zhu():
    return json.loads((FIXTURES / "crossref_zhu_doi.json").read_text(encoding="utf-8"))


@pytest.fixture()
def openalex_zhu():
    return json.loads((FIXTURES / "openalex_zhu_doi.json").read_text(encoding="utf-8"))


def test_parse_crossref_item_returns_publication(crossref_zhu):
    item = crossref_zhu["message"]
    pub = _parse_crossref_item(item)
    assert pub.doi == ZHU_DOI
    assert pub.year == 2024
    assert pub.publication_type == "article"
    assert pub.authors == ["Vivien Jiaqian Zhu"]
    assert "Comparative Literature" in pub.venue
    assert pub.match_status == "matched"


def test_parse_openalex_item_returns_publication(openalex_zhu):
    pub = _parse_openalex_item(openalex_zhu)
    assert pub.doi == ZHU_DOI
    assert pub.year == 2024
    assert pub.openalex_id == "https://openalex.org/W4408934567"
    assert pub.authors == ["Vivien Jiaqian Zhu"]
    assert pub.match_status == "matched"


def test_doi_fetcher_uses_crossref_then_openalex(crossref_zhu, openalex_zhu, monkeypatch):
    call_log: list[str] = []

    def fake_get_json(self, url):
        call_log.append(url)
        if "crossref" in url:
            return crossref_zhu
        if "openalex" in url:
            return openalex_zhu
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(DoiFetcher, "_get_json", fake_get_json)

    fetcher = DoiFetcher(sleeper=lambda: None)
    pub = fetcher.fetch(ZHU_DOI)

    assert pub is not None
    assert pub.doi == ZHU_DOI
    assert pub.openalex_id == "https://openalex.org/W4408934567"
    assert pub.year == 2024
    assert pub.match_status == "matched"
    assert any("crossref" in u for u in call_log)
    assert any("openalex" in u for u in call_log)


def test_doi_fetcher_falls_back_to_openalex_on_crossref_error(openalex_zhu, monkeypatch):
    def fake_get_json(self, url):
        if "crossref" in url:
            raise RuntimeError("crossref down")
        return openalex_zhu

    monkeypatch.setattr(DoiFetcher, "_get_json", fake_get_json)

    fetcher = DoiFetcher(sleeper=lambda: None)
    pub = fetcher.fetch(ZHU_DOI)

    assert pub is not None
    assert pub.doi == ZHU_DOI
    assert pub.openalex_id == "https://openalex.org/W4408934567"


def test_add_command_stores_publication(tmp_path, crossref_zhu, openalex_zhu, monkeypatch):
    from citewatch.cli import build_parser

    def fake_get_json(self, url):
        if "crossref" in url:
            return crossref_zhu
        return openalex_zhu

    monkeypatch.setattr(DoiFetcher, "_get_json", fake_get_json)

    db = tmp_path / "test.db"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", ZHU_DOI])
    rc = args.func(args)

    assert rc == 0
    store = Store(str(db))
    pub = store.get_by_doi(ZHU_DOI)
    assert pub is not None
    assert pub.year == 2024


def test_add_command_dedupes_by_doi(tmp_path, crossref_zhu, openalex_zhu, monkeypatch, capsys):
    from citewatch.cli import build_parser

    def fake_get_json(self, url):
        if "crossref" in url:
            return crossref_zhu
        return openalex_zhu

    monkeypatch.setattr(DoiFetcher, "_get_json", fake_get_json)

    db = tmp_path / "test.db"
    parser = build_parser()

    # First add
    args = parser.parse_args(["--db", str(db), "add", ZHU_DOI])
    args.func(args)
    capsys.readouterr()  # discard first-add output

    # Second add → duplicate
    args2 = parser.parse_args(["--db", str(db), "add", ZHU_DOI])
    rc = args2.func(args2)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["status"] == "duplicate"


def test_add_command_dedupes_by_fuzzy_title(tmp_path, crossref_zhu, openalex_zhu, monkeypatch):
    import sys

    from citewatch.cli import build_parser

    def fake_get_json(self, url):
        if "crossref" in url:
            return crossref_zhu
        return openalex_zhu

    monkeypatch.setattr(DoiFetcher, "_get_json", fake_get_json)

    db = tmp_path / "test.db"
    store = Store(str(db))
    # Seed a publication with the same title but no DOI
    store.add_publications([Publication(title=ZHU_TITLE, year=2024)])

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", ZHU_DOI])
    captured = []

    class Cap:
        def write(self, s):
            captured.append(s)

        def flush(self):
            pass

    old = sys.stdout
    sys.stdout = Cap()
    rc = args.func(args)
    sys.stdout = old
    out = "".join(captured)
    data = json.loads(out)
    assert rc == 0
    assert data["status"] == "duplicate"
