from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    path = Path(pdf_path)
    if path.read_bytes()[:4] != b"%PDF":
        return path.read_text(encoding="utf-8")

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages)
