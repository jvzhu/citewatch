from citewatch.models import Publication
from citewatch.store import Store
from citewatch.validator import validate_citation

MULLANEY_CITATION = (
    'Mullaney, Thomas S. "Controlling the Kanjisphere: The Rise of the Sino-Japanese Typewriter '
    'and the Birth of CJK." The Journal of Asian Studies 75, no. 3 (2016): 725-753. '
    'DOI: 10.1017/S0021911816000577'
)


def _seed_mullaney(store: Store) -> None:
    store.add_publications(
        [
            Publication(
                title=(
                    "Controlling the Kanjisphere: The Rise of the Sino-Japanese "
                    "Typewriter and the Birth of CJK"
                ),
                year=2016,
                venue="The Journal of Asian Studies",
                publication_type="article",
                authors=["Thomas S. Mullaney"],
                doi="10.1017/S0021911816000577",
                openalex_id="https://openalex.org/W1985059706",
                match_status="matched",
            )
        ]
    )


def test_validator_ok_and_mismatch_cases(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite3")
    _seed_mullaney(store)

    ok = validate_citation(MULLANEY_CITATION, store)
    assert ok.status == "ok"

    wrong_year = validate_citation(MULLANEY_CITATION.replace("(2016)", "(2017)"), store)
    assert wrong_year.status == "mismatch"
    assert wrong_year.diffs["year"] == {"expected": 2016, "actual": 2017}

    misspelled = validate_citation(MULLANEY_CITATION.replace("Kanjisphere", "Kanjispehre"), store)
    assert misspelled.status == "mismatch"
    assert "title" in misspelled.diffs


def test_validator_not_found_in_lurie_only_store(tmp_path) -> None:
    store = Store(tmp_path / "lurie.sqlite3")
    store.add_publications(
        [Publication(title="Realms of Literacy: Early Japan and the History of Writing", year=2011)]
    )

    result = validate_citation(MULLANEY_CITATION, store)
    assert result.status == "not-found"
