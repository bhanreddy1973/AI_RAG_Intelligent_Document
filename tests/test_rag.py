from app.rag import NOT_FOUND, ask, search
from app.schemas import SearchHit
from app.vectorstore import StoredChunk


class FakeDoc:
    class file_metadata:
        file_name = "Employment_Agreement.pdf"

    class document_metadata:
        document_type = "Employment Agreement"


def test_ask_returns_source_from_context(monkeypatch):
    monkeypatch.setattr("app.rag.settings.min_score", 0.1)
    monkeypatch.setattr("app.rag.embed_query", lambda query: [1.0, 0.0])
    monkeypatch.setattr("app.rag.get_document", lambda document_id: FakeDoc)
    monkeypatch.setattr(
        "app.rag.get_store",
        lambda: type(
            "S",
            (),
            {
                "search": lambda self, vector, top_k, document_id=None: [
                    StoredChunk(
                        chunk_id="doc-0",
                        document_id="doc",
                        text="The employee shall provide a notice period of 60 days.",
                        page_number=4,
                        score=0.9,
                    )
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        "app.rag.chat_json",
        lambda messages, max_tokens=400: {"answer": "60 days.", "chunk_id": "doc-0"},
    )

    result = ask("What is the notice period?")
    assert result.answer == "60 days."
    assert result.source == "Employment_Agreement.pdf"
    assert result.page == 4
    assert result.chunk_id == "doc-0"
    assert "60 days" in (result.supporting_text or "")


def test_ask_not_found_when_score_is_low(monkeypatch):
    monkeypatch.setattr("app.rag.settings.min_score", 0.8)
    monkeypatch.setattr("app.rag.embed_query", lambda query: [1.0])
    monkeypatch.setattr("app.rag.get_document", lambda document_id: FakeDoc)
    monkeypatch.setattr(
        "app.rag.get_store",
        lambda: type(
            "S",
            (),
            {
                "search": lambda self, vector, top_k, document_id=None: [
                    StoredChunk(
                        chunk_id="x",
                        document_id="d",
                        text="unrelated",
                        page_number=1,
                        score=0.2,
                    )
                ]
            },
        )(),
    )

    result = ask("What is the budget?")
    assert result.answer == NOT_FOUND
    assert result.source is None


def test_search_maps_hits(monkeypatch):
    monkeypatch.setattr("app.rag.embed_query", lambda query: [1.0, 0.0])
    monkeypatch.setattr("app.rag.get_document", lambda document_id: FakeDoc)
    monkeypatch.setattr(
        "app.rag.get_store",
        lambda: type(
            "S",
            (),
            {
                "search": lambda self, vector, top_k, document_id=None: [
                    StoredChunk(
                        chunk_id="c1",
                        document_id="d1",
                        text="hello",
                        page_number=2,
                        score=0.7,
                    )
                ]
            },
        )(),
    )
    hits = search("hello")
    assert hits == [
        SearchHit(
            document_id="d1",
            file_name="Employment_Agreement.pdf",
            page=2,
            chunk_id="c1",
            score=0.7,
            text="hello",
        )
    ]
