from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import requests

from citewatch.matcher import ScholarlyMatcher
from citewatch.parser.extract import extract_publications
from citewatch.parser.pdf import extract_text_from_pdf
from citewatch.store import Store
from citewatch.tracker import CitationTracker, track
from citewatch.validator import validate_many


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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
