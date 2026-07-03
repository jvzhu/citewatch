from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import requests
from rapidfuzz import fuzz

from citewatch.fetcher import DoiFetcher
from citewatch.matcher import ScholarlyMatcher
from citewatch.orcid import OrcidClient, _orcid_summary_to_publication
from citewatch.parser.extract import extract_publications
from citewatch.parser.pdf import extract_text_from_pdf
from citewatch.store import Store
from citewatch.tracker import CitationTracker, track
from citewatch.validator import validate_many

_FUZZY_DEDUPE_THRESHOLD = 85


def _parse_command(args: argparse.Namespace) -> int:
    source = args.source
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            temp_file.flush()
            text = extract_text_from_pdf(temp_file.name)
    else:
        text = extract_text_from_pdf(source)

    publications = extract_publications(text)
    store = Store(args.db)
    store.add_publications(publications)
    print(json.dumps([asdict(pub) for pub in publications], ensure_ascii=False, indent=2))
    return 0


def _track_command(args: argparse.Namespace) -> int:
    store = Store(args.db)
    matcher = ScholarlyMatcher(contact_email=args.email)
    tracker = CitationTracker(contact_email=args.email)
    results = track(store, matcher, tracker, diff=args.diff)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    citations: list[str] = []
    if args.file:
        citations.extend(Path(args.file).read_text(encoding="utf-8").splitlines())
    if args.citation:
        citations.append(args.citation)

    store = Store(args.db)
    results = validate_many(citations, store)
    print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    has_mismatch = any(result.status == "mismatch" for result in results)
    return 1 if has_mismatch else 0


def _add_command(args: argparse.Namespace) -> int:
    doi = args.doi.strip()
    store = Store(args.db)

    # Dedupe: exact DOI match
    existing = store.get_by_doi(doi)
    if existing:
        print(
            json.dumps(
                {"status": "duplicate", "doi": doi, "existing_id": existing.id},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # Fetch canonical metadata
    fetcher = DoiFetcher(contact_email=args.email)
    pub = fetcher.fetch(doi)
    if pub is None:
        print(json.dumps({"status": "not-found", "doi": doi}, ensure_ascii=False, indent=2))
        return 1

    # Dedupe: fuzzy title match against existing publications
    for existing_pub in store.list_publications():
        score = fuzz.token_set_ratio(pub.title, existing_pub.title)
        if pub.title and score >= _FUZZY_DEDUPE_THRESHOLD:
            print(
                json.dumps(
                    {
                        "status": "duplicate",
                        "doi": doi,
                        "existing_id": existing_pub.id,
                        "existing_title": existing_pub.title,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

    store.add_publications([pub])
    # Retrieve the newly inserted record to get its assigned id
    added = store.get_by_doi(doi) if doi else None
    result = {
        "status": "added",
        "doi": doi,
        "title": pub.title,
        "year": pub.year,
        "id": added.id if added else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _orcid_command(args: argparse.Namespace) -> int:
    orcid_id = args.orcid_id.strip()
    store = Store(args.db)
    client = OrcidClient(contact_email=args.email)
    fetcher = DoiFetcher(contact_email=args.email)

    entries = client.fetch_works(orcid_id)
    results: list[dict] = []

    for entry in entries:
        doi = entry["doi"]
        summary = entry["summary"]

        # Dedupe: exact DOI match
        if doi:
            existing = store.get_by_doi(doi)
            if existing:
                results.append({"status": "duplicate", "doi": doi, "existing_id": existing.id})
                continue

        # Build publication object
        pub = None
        if doi:
            pub = fetcher.fetch(doi)
        if pub is None:
            # Use ORCID metadata; flag as unresolved when no DOI was found
            pub = _orcid_summary_to_publication(summary)
            if doi:
                pub.doi = doi
            else:
                pub.match_status = "unresolved"

        if not pub.title:
            results.append({"status": "skipped", "reason": "empty title"})
            continue

        # Dedupe: fuzzy title match
        is_dup = any(
            fuzz.token_set_ratio(pub.title, ep.title) >= _FUZZY_DEDUPE_THRESHOLD
            for ep in store.list_publications()
        )
        if is_dup:
            results.append({"status": "duplicate", "title": pub.title})
            continue

        store.add_publications([pub])
        results.append({"status": "added", "doi": doi, "title": pub.title})

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def _report_command(args: argparse.Namespace) -> int:
    from citewatch.report import render_report

    store = Store(args.db)
    html = render_report(store)
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print(f"Report written to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="citewatch")
    parser.add_argument("--db", default="citewatch.db")
    parser.add_argument("--email", default="citewatch@example.com")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse")
    parse_cmd.add_argument("source")
    parse_cmd.set_defaults(func=_parse_command)

    track_cmd = sub.add_parser("track")
    track_cmd.add_argument("--diff", action="store_true")
    track_cmd.set_defaults(func=_track_command)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("citation", nargs="?")
    validate_cmd.add_argument("--file")
    validate_cmd.set_defaults(func=_validate_command)

    add_cmd = sub.add_parser("add", help="Register a publication by DOI")
    add_cmd.add_argument("doi", help="DOI to fetch and store")
    add_cmd.set_defaults(func=_add_command)

    orcid_cmd = sub.add_parser("orcid", help="Import publications from an ORCID profile")
    orcid_cmd.add_argument("orcid_id", help="ORCID iD (e.g. 0000-0002-1789-5272)")
    orcid_cmd.set_defaults(func=_orcid_command)

    report_cmd = sub.add_parser("report", help="Generate an HTML citation report")
    report_cmd.add_argument("--out", default="report.html", help="Output file path")
    report_cmd.set_defaults(func=_report_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
