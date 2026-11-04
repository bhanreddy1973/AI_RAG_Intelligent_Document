import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.nvidia_client import LLMError
from app.schemas import DocumentType, EmploymentAgreement, ExtractedField
from app.summarizer import DocumentOverview
from app.vectorstore import reset_store


def fake_summarize(pages):
    return DocumentOverview(
        title="Employment Agreement",
        short_summary="Notice period is 60 days.",
        key_topics=["Termination"],
        entities=["ABC Technologies"],
        batch_summaries=[],
    )


def fake_classify(summary, title=""):
    return DocumentType.EMPLOYMENT_AGREEMENT


def fake_extract(pages, document_type):
    return EmploymentAgreement(
        notice_period=ExtractedField(value="60 days", page=1),
        company_name=ExtractedField(value="ABC Technologies", page=1),
    )


def fake_embed_chunks(chunks, **kwargs):
    return [[1.0, 0.0] for _ in chunks]


def fake_embed_query(text):
    return [1.0, 0.0]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "app.db"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "faiss_index_path", str(tmp_path / "faiss.index"))
    monkeypatch.setattr(settings, "faiss_meta_path", str(tmp_path / "faiss_meta.json"))
    reset_store()

    monkeypatch.setattr("app.main.summarize_pages", fake_summarize)
    monkeypatch.setattr("app.main.classify_document", fake_classify)
    monkeypatch.setattr("app.main.extract_fields", fake_extract)
    monkeypatch.setattr("app.main.embed_chunks", fake_embed_chunks)
    monkeypatch.setattr("app.rag.embed_query", fake_embed_query)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    reset_store()


def test_upload_list_and_get(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("agreement.txt", b"The notice period is 60 days.", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["duplicate"] is False
    document_id = body["document"]["document_id"]
    assert body["document"]["extracted_data"]["notice_period"]["value"] == "60 days"

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert listed.json()[0]["document_id"] == document_id

    detail = client.get(f"/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["file_metadata"]["file_name"] == "agreement.txt"


def test_duplicate_upload_is_skipped(client):
    payload = {"file": ("agreement.txt", b"same bytes twice", "text/plain")}
    first = client.post("/documents/upload", files=payload)
    second = client.post("/documents/upload", files=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["document"]["document_id"] == second.json()["document"]["document_id"]


def test_invalid_file_type(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("notes.docx", b"not allowed", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_empty_file(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400


def test_missing_document(client):
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404


def test_search_and_ask(client, monkeypatch):
    client.post(
        "/documents/upload",
        files={"file": ("agreement.txt", b"The notice period is 60 days.", "text/plain")},
    )
    monkeypatch.setattr(
        "app.rag.chat_json",
        lambda messages, max_tokens=400: {"answer": "60 days.", "chunk_id": None},
    )

    search = client.post("/search", json={"query": "notice period"})
    assert search.status_code == 200
    assert search.json()["results"]

    asked = client.post("/ask", json={"query": "What is the notice period?"})
    assert asked.status_code == 200
    body = asked.json()
    assert body["answer"] == "60 days."
    assert body["source"] == "agreement.txt"
    assert body["page"] is not None
    assert body["supporting_text"]


def test_ask_empty_query(client):
    response = client.post("/ask", json={"query": "   "})
    assert response.status_code == 400


def test_llm_failure_returns_502(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.summarize_pages",
        lambda pages: (_ for _ in ()).throw(LLMError("timeout")),
    )
    response = client.post(
        "/documents/upload",
        files={"file": ("agreement.txt", b"The notice period is 60 days.", "text/plain")},
    )
    assert response.status_code == 502
