# citewatch

`citewatch` is an MVP pipeline for humanities-oriented citation intelligence:

1. Parse an academic CV (PDF) and extract publications.
2. Seed publications directly by DOI (no CV required).
3. Import publications from an ORCID profile.
4. Track citations with Crossref + OpenAlex.
5. Validate free-form references against canonical metadata.
6. Generate a self-contained HTML citation report.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Quick start

Seed a publication, track citations, and generate a report in three commands:

```bash
citewatch --db citewatch.db --email you@example.com add 10.1080/25723618.2024.2433301
citewatch --db citewatch.db --email you@example.com track --diff
citewatch --db citewatch.db report --out report.html
```

The example above uses the following real publication as the worked example:

> Zhu, Vivien Jiaqian. "'I Dwell in Possibility': The Poetics of Space in the Works of 1980s
> Japanese Avant-Garde Fashion Designers." *Comparative Literature: East & West* 8, no. 2 (2024).
> DOI: [10.1080/25723618.2024.2433301](https://doi.org/10.1080/25723618.2024.2433301)

## CLI

### Parse a CV

```bash
citewatch --db citewatch.db parse tests/fixtures/Lurie-CV.pdf
```

This stores extracted publications locally and prints JSON.

### Add a publication by DOI

```bash
citewatch --db citewatch.db --email you@example.com add 10.1080/25723618.2024.2433301
```

Fetches canonical metadata from Crossref (with OpenAlex fallback) and stores the publication.
Deduplicates against existing records by exact DOI and fuzzy title match.
The publication is immediately available to `track` / `track --diff`.

### Import from ORCID

```bash
citewatch --db citewatch.db --email you@example.com orcid 0000-0002-1789-5272
```

Imports all works from the given ORCID iD via the ORCID public API. Works with DOIs are resolved
via Crossref/OpenAlex; works without DOIs are stored with ORCID metadata and flagged as
`unresolved`. All imports are deduplicated against existing DB entries.

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

### Generate an HTML report

```bash
citewatch --db citewatch.db report --out report.html
```

Produces a self-contained static HTML file (inline CSS, no JavaScript build step) that includes:

- Publication list with per-publication citation counts.
- Per-publication citing works (linked to OpenAlex).
- A "New since last snapshot" section showing works that appeared after the previous `track` run.

## Scheduled tracking with GitHub Actions

The repository ships `.github/workflows/track.yml`, which runs weekly (Monday 06:00 UTC) and on
`workflow_dispatch`. It:

1. **Restores the SQLite DB** between runs via `actions/cache` keyed on a stable prefix.  
   *Trade-off*: the GitHub Actions cache can be evicted after 7 days of inactivity, which is
   acceptable for a low-volume personal tool. For higher durability, commit a snapshot or use
   object storage (e.g. S3).

2. **Seeds publications** from `dois.txt` (one DOI per line, `#` comments supported).

3. **Runs `track --diff`** and, if new citing works are found, opens (or updates) a single
   rolling GitHub issue labelled `citations`.

4. **Uploads `report.html`** as a workflow artifact after every run.

5. **Reads the contact email** from the `CITEWATCH_EMAIL` repository variable (Settings →
   Secrets and variables → Actions → Variables). Falls back to `citewatch@example.com` if unset.

To enable the workflow: add at least one DOI to `dois.txt`, set the `CITEWATCH_EMAIL` variable,
and ensure the repository has the `citations` label (or let the first run create the issue without
it, then add the label manually).

## Fixtures and tests

- `tests/fixtures/Lurie-CV.pdf`: seed CV fixture used in parser tests.
- `tests/fixtures/crossref_mullaney_10.1017_S0021911816000577.json`: canonical Crossref work
  metadata fixture for DOI `10.1017/S0021911816000577`.
- `tests/fixtures/crossref_search_mullaney.json`: Crossref title-search response fixture (includes
  a distractor item to exercise fuzzy matching).
- `tests/fixtures/crossref_zhu_doi.json`: Crossref direct DOI response for
  `10.1080/25723618.2024.2433301` (Zhu 2024).
- `tests/fixtures/openalex_mullaney_work.json`: OpenAlex work fixture.
- `tests/fixtures/openalex_search_mullaney.json`: OpenAlex search response fixture (includes a
  distractor item to exercise fuzzy matching).
- `tests/fixtures/openalex_zhu_doi.json`: OpenAlex work fixture for `10.1080/25723618.2024.2433301`.
- `tests/fixtures/openalex_citing_mullaney_page*.json`: citing-works snapshot fixtures for tracker snapshot/diff tests. Despite the `page` naming, these are not pagination pages: they are two successive snapshot payloads (first run vs second run) used to drive the `--diff` assertion. Mullaney (2016) does not appear among the OpenAlex citing works of Lurie's *Realms of Literacy* (2011), so the tracker tests use the article's own citing works as an explicitly mocked linkage.
- `tests/fixtures/orcid_works_0000-0002-1789-5272.json`: ORCID public API works response for
  ORCID iD `0000-0002-1789-5272` (includes one work with a DOI and one without).

All API interactions in tests use these fixtures; no live network calls are made.

Run checks:

```bash
ruff check .
pytest -q
```
