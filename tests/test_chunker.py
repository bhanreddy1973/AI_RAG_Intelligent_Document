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
    assert len(chunks[0].text) <= 20
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


def test_prefers_paragraph_boundaries(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 40)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 5)
    pages = [
        Page(
            1,
            "First paragraph about notice.\n\n"
            "Second paragraph about salary details here.",
        )
    ]
    chunks = chunk_pages(pages, "doc-2")

    assert len(chunks) >= 2
    assert "First paragraph about notice." in chunks[0].text
    assert "Second paragraph" in chunks[1].text
    # Should not hard-cut mid-paragraph when a paragraph fits in size.
    assert not chunks[0].text.endswith("about noti")


def test_prefers_sentence_boundaries_over_mid_word_cuts(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 50)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 8)
    text = (
        "The employee shall provide sixty days notice. "
        "Salary is paid monthly in Indian rupees."
    )
    pages = [Page(1, text)]
    chunks = chunk_pages(pages, "doc-3")

    assert len(chunks) >= 2
    assert chunks[0].text.rstrip().endswith("notice.")
    assert "Salary is paid" in chunks[1].text


def test_chunks_stay_within_size(monkeypatch):
    monkeypatch.setattr("app.chunker.settings.chunk_size", 30)
    monkeypatch.setattr("app.chunker.settings.chunk_overlap", 5)
    pages = [
        Page(
            1,
            "Alpha sentence one is here. Beta sentence two is here. "
            "Gamma sentence three finishes.",
        )
    ]
    chunks = chunk_pages(pages, "doc-4")

    assert chunks
    assert all(len(chunk.text) <= 30 for chunk in chunks)
