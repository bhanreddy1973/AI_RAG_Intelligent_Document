import numpy as np

from app.chunker import Chunk
from app.embeddings import (
    build_chunk_embed_text,
    embed_chunks,
    embed_query,
    embed_texts,
)


class FakeModel:
    def encode(self, texts, normalize_embeddings=True):
        return np.array([[float(len(text)), 0.5] for text in texts], dtype=float)


def test_embed_texts(monkeypatch):
    monkeypatch.setattr("app.embeddings.get_model", lambda: FakeModel())
    vectors = embed_texts(["hi", "notice period"])
    assert len(vectors) == 2
    assert vectors[0][0] == 2.0
    assert vectors[1][0] == float(len("notice period"))


def test_embed_query(monkeypatch):
    monkeypatch.setattr("app.embeddings.get_model", lambda: FakeModel())
    vector = embed_query("abc")
    assert vector == [3.0, 0.5]


def test_embed_empty_list(monkeypatch):
    monkeypatch.setattr("app.embeddings.get_model", lambda: FakeModel())
    assert embed_texts([]) == []


def test_embed_text_includes_metadata_and_chunk():
    text = build_chunk_embed_text(
        "The notice period is 60 days.",
        file_name="Employment_Agreement.pdf",
        document_type="Employment Agreement",
        title="Employment Agreement - John Doe",
        short_summary="Covers notice and pay.",
    )
    assert "Employment_Agreement.pdf" in text
    assert "Employment Agreement" in text
    assert "Covers notice and pay." in text
    assert text.endswith("The notice period is 60 days.")


def test_embed_chunks_uses_metadata_context(monkeypatch):
    seen = []

    class CaptureModel:
        def encode(self, texts, normalize_embeddings=True):
            seen.extend(texts)
            return np.array([[1.0, 0.0] for _ in texts], dtype=float)

    monkeypatch.setattr("app.embeddings.get_model", lambda: CaptureModel())
    chunk = Chunk(
        chunk_id="c1",
        document_id="d1",
        page_number=4,
        chunk_index=0,
        text="Notice period of 60 days",
    )
    embed_chunks(
        [chunk],
        file_name="Employment_Agreement.pdf",
        document_type="Employment Agreement",
        title="EA",
        short_summary="Notice terms",
    )
    assert len(seen) == 1
    assert "Employment_Agreement.pdf" in seen[0]
    assert "Notice period of 60 days" in seen[0]
