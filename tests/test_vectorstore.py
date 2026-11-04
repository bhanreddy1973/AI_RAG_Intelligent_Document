from app.chunker import Chunk
from app.vectorstore import VectorStore, reset_store


def _chunk(chunk_id, document_id, text, page=1):
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        page_number=page,
        chunk_index=0,
        text=text,
    )


def test_add_and_search_nearest(tmp_path, monkeypatch):
    monkeypatch.setattr("app.vectorstore.settings.faiss_index_path", str(tmp_path / "faiss.index"))
    monkeypatch.setattr("app.vectorstore.settings.faiss_meta_path", str(tmp_path / "faiss_meta.json"))
    reset_store()
    store = VectorStore()
    store.add_chunks(
        [_chunk("c1", "d1", "notice period 60 days"), _chunk("c2", "d1", "salary details")],
        [[1.0, 0.0], [0.0, 1.0]],
    )

    hits = store.search([1.0, 0.0], top_k=1)
    assert len(hits) == 1
    assert hits[0].chunk_id == "c1"
    assert hits[0].document_id == "d1"
    assert hits[0].text.startswith("notice period")
    assert "file_name" not in store.items[0]


def test_filter_by_document_id(tmp_path, monkeypatch):
    monkeypatch.setattr("app.vectorstore.settings.faiss_index_path", str(tmp_path / "faiss.index"))
    monkeypatch.setattr("app.vectorstore.settings.faiss_meta_path", str(tmp_path / "faiss_meta.json"))
    reset_store()
    store = VectorStore()
    store.add_chunks([_chunk("c1", "d1", "from doc one")], [[1.0, 0.0]])
    store.add_chunks([_chunk("c2", "d2", "from doc two")], [[0.9, 0.1]])

    hits = store.search([1.0, 0.0], top_k=5, document_id="d2")
    assert len(hits) == 1
    assert hits[0].document_id == "d2"


def test_empty_store_returns_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.vectorstore.settings.faiss_index_path", str(tmp_path / "missing.index"))
    monkeypatch.setattr("app.vectorstore.settings.faiss_meta_path", str(tmp_path / "missing.json"))
    reset_store()
    store = VectorStore()
    assert store.search([1.0, 0.0], top_k=3) == []
