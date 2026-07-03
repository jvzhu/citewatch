# citewatch

`citewatch` is an MVP pipeline for humanities-oriented citation intelligence:

1. Parse an academic CV (PDF) and extract publications.
2. Track citations with Crossref + OpenAlex.
3. Validate free-form references against canonical metadata.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## CLI

### Parse a CV

```bash
citewatch --db citewatch.db parse tests/fixtures/Lurie-CV.pdf
```

This stores extracted publications locally and prints JSON.

### Track citations

```bash
citewatch --db citewatch.db --email you@example.com track
citewatch --db citewatch.db --email you@example.com track --diff
```

`--diff` reports newly observed citing works since the prior snapshot.

### Validate citation strings

```bash
citewatch --db citewatch.db validate 'Mullaney, Thomas S. "Controlling the Kanjisphere..." (2016).'
citewatch --db citewatch.db validate --file refs.txt
```

Exit code is `1` if any citation is a `mismatch`, otherwise `0`.

## Fixtures and tests

- `tests/fixtures/Lurie-CV.pdf`: seed CV fixture used in parser tests.
- `tests/fixtures/crossref_mullaney_10.1017_S0021911816000577.json`: canonical Crossref work metadata fixture for DOI `10.1017/S0021911816000577`.
- `tests/fixtures/crossref_search_mullaney.json`: Crossref title-search response fixture (includes a distractor item to exercise fuzzy matching).
- `tests/fixtures/openalex_mullaney_work.json`: OpenAlex work fixture.
- `tests/fixtures/openalex_search_mullaney.json`: OpenAlex search response fixture (includes a distractor item to exercise fuzzy matching).
- `tests/fixtures/openalex_citing_mullaney_page*.json`: recorded citing-works fixtures for tracker snapshot/diff tests. Mullaney (2016) does not appear among the OpenAlex citing works of Lurie's *Realms of Literacy* (2011), so the tracker tests use the article's own citing-works pages as an explicitly mocked linkage.

All API interactions in tests use these recorded responses; no live network calls are made.

Run checks:

```bash
ruff check .
pytest -q
```
