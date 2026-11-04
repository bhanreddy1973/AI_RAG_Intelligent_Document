from app.chunker import chunk_pages
from app.parser import Page


def test_short_page_is_one_chunk(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 1000)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 150)
    pages = [Page(1, "The notice period is 60 days.")]
    chunks = chunk_pages(pages, "doc-1")

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_id == "doc-1-0"
    assert "60 days" in chunks[0].text


def test_long_text_splits_with_overlap(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 20)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 5)
    pages = [Page(1, "abcdefghijklmnopqrstuvwxyz")]
    chunks = chunk_pages(pages, "doc-1")

    assert len(chunks) >= 2
    assert chunks[0].text.startswith("abcdefghijklmnopqrst")
    assert chunks[1].text.startswith(chunks[0].text[-5:])
    assert [item.chunk_index for item in chunks] == list(range(len(chunks)))


def test_page_numbers_are_kept(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 1000)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 150)
    pages = [Page(1, "page one text"), Page(4, "notice period 60 days")]
    chunks = chunk_pages(pages, "doc-9")

    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 4
    assert chunks[1].chunk_id == "doc-9-1"
