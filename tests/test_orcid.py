from __future__ import annotations

import json
from pathlib import Path

import pytest

from citewatch.fetcher import DoiFetcher
from citewatch.orcid import OrcidClient
from citewatch.store import Store

FIXTURES = Path(__file__).parent / "fixtures"

ORCID_ID = "0000-0002-1789-5272"
ZHU_DOI = "10.1080/25723618.2024.2433301"


@pytest.fixture()
def orcid_works():
    return json.loads(
        (FIXTURES / "orcid_works_0000-0002-1789-5272.json").read_text(encoding="utf-8")
    )


@pytest.fixture()
def crossref_zhu():
    return json.loads((FIXTURES / "crossref_zhu_doi.json").read_text(encoding="utf-8"))


@pytest.fixture()
def openalex_zhu():
    return json.loads((FIXTURES / "openalex_zhu_doi.json").read_text(encoding="utf-8"))


def test_orcid_client_parses_works(orcid_works, monkeypatch):
    def fake_get_json(self, url):
        return orcid_works

    monkeypatch.setattr(OrcidClient, "_get_json", fake_get_json)

    client = OrcidClient(sleeper=lambda: None)
    entries = client.fetch_works(ORCID_ID)

    assert len(entries) == 2
    # First entry has DOI
    assert entries[0]["doi"] == ZHU_DOI
    # Second entry has no DOI
    assert entries[1]["doi"] is None


def test_orcid_command_imports_and_dedupes(
    tmp_path, orcid_works, crossref_zhu, openalex_zhu, monkeypatch
):
    from citewatch.cli import build_parser

    def fake_orcid_get(self, url):
        return orcid_works

    def fake_doi_get(self, url):
        if "crossref" in url:
            return crossref_zhu
        return openalex_zhu

    monkeypatch.setattr(OrcidClient, "_get_json", fake_orcid_get)
    monkeypatch.setattr(DoiFetcher, "_get_json", fake_doi_get)

    db = tmp_path / "test.db"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "orcid", ORCID_ID])
    rc = args.func(args)

    assert rc == 0

    store = Store(str(db))
    pubs = store.list_publications()
    # Two works imported: one with DOI resolved, one unresolved
    assert len(pubs) == 2
    doi_pubs = [p for p in pubs if p.doi == ZHU_DOI]
    assert len(doi_pubs) == 1
    assert doi_pubs[0].year == 2024

    unresolved = [p for p in pubs if p.match_status == "unresolved"]
    assert len(unresolved) == 1


def test_orcid_command_dedupes_doi(
    tmp_path, orcid_works, crossref_zhu, openalex_zhu, monkeypatch
):
    from citewatch.cli import build_parser

    def fake_orcid_get(self, url):
        return orcid_works

    def fake_doi_get(self, url):
        if "crossref" in url:
            return crossref_zhu
        return openalex_zhu

    monkeypatch.setattr(OrcidClient, "_get_json", fake_orcid_get)
    monkeypatch.setattr(DoiFetcher, "_get_json", fake_doi_get)

    db = tmp_path / "test.db"
    parser = build_parser()

    # Run once
    args = parser.parse_args(["--db", str(db), "orcid", ORCID_ID])
    args.func(args)

    # Run again — everything should be deduplicated
    args2 = parser.parse_args(["--db", str(db), "orcid", ORCID_ID])
    import sys
    from io import StringIO

    captured = StringIO()
    old = sys.stdout
    sys.stdout = captured
    args2.func(args2)
    sys.stdout = old
    results = json.loads(captured.getvalue())

    assert all(r["status"] == "duplicate" for r in results)

    store = Store(str(db))
    # Count should still be 2 (no duplicates added)
    assert len(store.list_publications()) == 2
