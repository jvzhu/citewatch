from pathlib import Path

import pytest

from citewatch.parser.extract import extract_publications
from citewatch.parser.pdf import extract_text_from_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "Lurie-CV.pdf"


def test_extract_text_from_fixture_cv() -> None:
    text = extract_text_from_pdf(FIXTURE)
    assert "Realms of Literacy" in text
    assert "Man'yōshū" in text


def test_extract_publications_includes_known_lurie_works() -> None:
    text = extract_text_from_pdf(FIXTURE)
    publications = extract_publications(text)
    titles = {p.title for p in publications}

    assert "Realms of Literacy: Early Japan and the History of Writing" in titles
    assert "The Cambridge History of Japanese Literature" in titles
    assert "Sekai no mojishi to Man'yōshū" in titles
    assert "The Vernacular in the World of Wen: Sheldon Pollock's Model in East Asia?" in titles
    assert "Japanese Lexicography from ca. 1800 to the Present," in titles
    assert (
        "Language, Writing, and Disciplinarity in the Critique of the "
        "'Ideographic Myth': Some Proleptical Remarks,"
    ) in titles
    assert all(not publication.venue for publication in publications)


def test_extract_text_from_non_utf8_non_pdf_raises_clear_error(tmp_path) -> None:
    path = tmp_path / "binary.dat"
    path.write_bytes(b"\xff\xfe\x00\x01")

    with pytest.raises(ValueError, match="is not a PDF and is not valid UTF-8 text"):
        extract_text_from_pdf(path)
