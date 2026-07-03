import json
from pathlib import Path

import pytest

from citewatch.models import Publication
from citewatch.store import Store
from citewatch.tracker import track


class FakeMatcher:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, _publication):
        self.calls += 1
        return (
            "10.1017/S0021911816000577",
            "https://openalex.org/W1985059706",
            "matched",
        )


class FakeTracker:
    def __init__(self, first_ids, second_ids) -> None:
        self.responses = [(2, first_ids), (3, second_ids)]
        self.index = 0

    def fetch_citing_works(self, _openalex_id):
        value = self.responses[self.index]
        if self.index < len(self.responses) - 1:
            self.index += 1
        return value


def test_track_diff_reports_new_citations(tmp_path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    first_payload = json.loads((fixtures / "openalex_citing_mullaney_page1.json").read_text())
    second_payload = json.loads((fixtures / "openalex_citing_mullaney_page2.json").read_text())
    first_ids = [x["id"] for x in first_payload["results"]]
    second_ids = [x["id"] for x in second_payload["results"]]

    store = Store(tmp_path / "test.db")
    store.add_publications(
        [
            Publication(
                title=(
                    "Controlling the Kanjisphere: The Rise of the Sino-Japanese "
                    "Typewriter and the Birth of CJK"
                ),
                year=2016,
                publication_type="article",
            )
        ]
    )

    matcher = FakeMatcher()
    tracker = FakeTracker(first_ids, second_ids)

    first = track(store, matcher, tracker, diff=True)
    second = track(store, matcher, tracker, diff=True)

    assert first[0]["status"] == "tracked"
    assert "new_citations" not in first[0]
    assert second[0]["new_citations"] == ["https://openalex.org/W3000000003"]


def test_track_raises_when_publication_id_is_missing() -> None:
    class MissingIdStore:
        def list_publications(self):
            return [Publication(title="Untitled")]

    with pytest.raises(ValueError, match="must have a database id"):
        track(MissingIdStore(), FakeMatcher(), FakeTracker([], []))
