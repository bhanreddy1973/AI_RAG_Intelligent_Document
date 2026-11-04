from dataclasses import dataclass
from pathlib import Path

import fitz


ALLOWED_EXTENSIONS = {".pdf", ".txt"}


class ParseError(Exception):
    pass


@dataclass
class Page:
    page_number: int
    text: str


def extract_pages(file_path: str | Path) -> list[Page]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise ParseError(f"Unsupported file type: {suffix or 'unknown'}. Use PDF or TXT.")

    if not path.exists():
        raise ParseError(f"File not found: {path.name}")

    if suffix == ".pdf":
        pages = _read_pdf(path)
    else:
        pages = _read_txt(path)

    if not any(page.text.strip() for page in pages):
        raise ParseError("Document is empty or has no readable text.")

    return pages


def _read_pdf(path: Path) -> list[Page]:
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise ParseError(f"Could not read PDF: {path.name}") from exc

    pages = []
    try:
        for index, page in enumerate(doc, start=1):
            pages.append(Page(page_number=index, text=page.get_text("text").strip()))
    finally:
        doc.close()
    return pages


def _read_txt(path: Path) -> list[Page]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    except Exception as exc:
        raise ParseError(f"Could not read TXT: {path.name}") from exc

    return [Page(page_number=1, text=text.strip())]
