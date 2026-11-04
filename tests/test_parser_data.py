from pathlib import Path

import pytest

from app.config import ROOT_DIR
from app.parser import extract_pages

DATA_DIR = ROOT_DIR / "Data"
PDFS = sorted(p for p in DATA_DIR.glob("*.pdf") if p.is_file())


@pytest.mark.skipif(not PDFS, reason="No PDFs in Data/")
@pytest.mark.parametrize("pdf_path", PDFS, ids=lambda p: p.name)
def test_parser_reads_data_pdf(pdf_path: Path):
    pages = extract_pages(pdf_path)

    assert len(pages) >= 1
    assert [page.page_number for page in pages] == list(range(1, len(pages) + 1))
    assert any(page.text.strip() for page in pages)
