import numpy as np

from app.embeddings import embed_query, embed_texts


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
