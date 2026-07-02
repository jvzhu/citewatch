import json
from pathlib import Path

from citewatch.matcher import ScholarlyMatcher
from citewatch.models import Publication

FIXTURES = Path(__file__).parent / "fixtures"


def test_matcher_resolves_mullaney_doi_and_openalex_id(monkeypatch) -> None:
    crossref = json.loads(
        (FIXTURES / "crossref_search_mullaney.json").read_text(encoding="utf-8")
    )
    openalex = json.loads(
        (FIXTURES / "openalex_search_mullaney.json").read_text(encoding="utf-8")
    )

    def fake_get_json(self, url, params):
        if "crossref" in url:
            return crossref
        if "openalex" in url:
            return openalex
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(ScholarlyMatcher, "_get_json", fake_get_json)

    matcher = ScholarlyMatcher(sleeper=lambda: None)
    pub = Publication(
        title=(
            "Controlling the Kanjisphere: The Rise of the Sino-Japanese "
            "Typewriter and the Birth of CJK"
        ),
        year=2016,
    )

    doi, openalex_id, status = matcher.resolve(pub)

    assert doi == "10.1017/S0021911816000577"
    assert openalex_id == "https://openalex.org/W1985059706"
    assert status == "matched"
