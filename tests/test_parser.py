from pathlib import Path

import fitz
import pytest

from app.parser import ParseError, extract_pages


def test_txt_is_page_one(tmp_path: Path):
    path = tmp_path / "agreement.txt"
    path.write_text("The notice period is 60 days.", encoding="utf-8")

    pages = extract_pages(path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "60 days" in pages[0].text


def test_pdf_keeps_page_numbers(tmp_path: Path):
    path = tmp_path / "policy.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Work from home policy")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Manager approval is required")
    doc.save(path)
    doc.close()

    pages = extract_pages(path)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "policy" in pages[0].text.lower()
    assert "approval" in pages[1].text.lower()


def test_unsupported_file_type(tmp_path: Path):
    path = tmp_path / "notes.docx"
    path.write_text("not supported")

    with pytest.raises(ParseError, match="Unsupported file type"):
        extract_pages(path)


def test_missing_file(tmp_path: Path):
    with pytest.raises(ParseError, match="File not found"):
        extract_pages(tmp_path / "missing.txt")


def test_empty_txt(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("   \n", encoding="utf-8")

    with pytest.raises(ParseError, match="empty"):
        extract_pages(path)


def test_empty_pdf(tmp_path: Path):
    path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()

    with pytest.raises(ParseError, match="empty"):
        extract_pages(path)
