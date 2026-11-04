"""Live automated cases: every sample file goes through the full pipeline.

Files → POST /documents/upload → parse → summarize → classify → extract →
chunk → embed → SQLite + FAISS → list / get / search / ask.

Storage paths come from .env (Data/app.db, Data/uploads, Data/faiss.*).
LLM and embeddings are NOT mocked.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT_DIR, settings
from app.vectorstore import reset_store

TEST_DATA = ROOT_DIR / "TEST_DATA"
DATA_DIR = ROOT_DIR / "Data"

EMPLOYMENT_01 = TEST_DATA / "employment_agreement_01.txt"
POLICY_01 = TEST_DATA / "company_policy_01.txt"
PRODUCT_01 = TEST_DATA / "product_documentation_01.txt"
TECH_01 = TEST_DATA / "technical_specification_01.txt"
TEMPLATE_PDF = DATA_DIR / "Template_Employment_Agreement.pdf"

# All five samples must run the full upload pipeline.
CORPUS_FILES = [
    EMPLOYMENT_01,
    POLICY_01,
    PRODUCT_01,
    TECH_01,
    TEMPLATE_PDF,
]


pytestmark = pytest.mark.skipif(
    not TEST_DATA.is_dir(),
    reason="TEST_DATA/ folder is missing",
)


def _llm_ready() -> bool:
    provider = (settings.llm_provider or "nvidia").lower()
    if provider == "openai":
        return bool(settings.openai_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    return bool(settings.nvidia_api_key)


def _require_live_llm():
    if not _llm_ready():
        pytest.skip(
            f"Live LLM key missing for LLM_PROVIDER={settings.llm_provider!r}. "
            "Set the matching API key in .env to run real endpoint tests."
        )


def _content_type(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "application/pdf"
    return "text/plain"


def _search_query_for(path: Path) -> str:
    name = path.name.lower()
    if "employment" in name:
        return "Notice period reference"
    if "policy" in name:
        return "Cedarline Technologies policy"
    if "product" in name:
        return "LedgerFlow product"
    if "technical" in name:
        return "Meridian Identity Service"
    return "employment agreement"


@pytest.fixture
def live_client():
    """Use real SQLITE_PATH / UPLOAD_DIR / FAISS paths from settings (.env)."""
    _require_live_llm()
    reset_store()
    from app.main import app

    with TestClient(app) as client:
        yield client
    reset_store()


def test_1_corpus_files_exist():
    """All five sample paths must be present before the live pipeline runs."""
    missing = [str(path) for path in CORPUS_FILES if not path.is_file()]
    assert not missing, f"Missing sample files: {missing}"


def test_2_upload_all_five_full_pipeline(live_client):
    """
    Upload each of the five files through the real API.

    Full steps per file: save → parse → summarize → classify → extract →
    chunk → embed → SQLite + FAISS.
    Then list, get, and search each document.
    """
    client = live_client
    uploaded = {}

    for path in CORPUS_FILES:
        assert path.is_file(), f"Missing {path}"
        response = client.post(
            "/documents/upload",
            files={"file": (path.name, path.read_bytes(), _content_type(path))},
        )
        assert response.status_code == 200, f"{path.name}: {response.text}"
        body = response.json()["document"]
        uploaded[path.name] = body

        assert body["file_metadata"]["file_name"] == path.name
        assert body["document_metadata"]["document_type"]
        assert body["processing_metadata"]["status"] == "completed"
        assert body["extracted_data"]
        assert body["document_id"]

    assert settings.resolve(settings.sqlite_path).exists()
    assert settings.resolve(settings.upload_dir).exists()
    assert settings.resolve(settings.faiss_index_path).exists()
    assert settings.resolve(settings.faiss_meta_path).exists()

    listed = client.get("/documents")
    assert listed.status_code == 200
    listed_names = {item["file_name"] for item in listed.json()}
    for path in CORPUS_FILES:
        assert path.name in listed_names, f"{path.name} missing from GET /documents"

    assert len(listed_names) >= 5

    for path in CORPUS_FILES:
        document_id = uploaded[path.name]["document_id"]
        detail = client.get(f"/documents/{document_id}")
        assert detail.status_code == 200, path.name
        assert detail.json()["document_id"] == document_id
        assert detail.json()["extracted_data"]

        search = client.post(
            "/search",
            json={
                "query": _search_query_for(path),
                "document_id": document_id,
                "top_k": 3,
            },
        )
        assert search.status_code == 200, f"search {path.name}: {search.text}"
        assert search.json()["results"], f"No search hits for {path.name}"


def test_3_ask_notice_period_on_employment(live_client):
    """Live POST /ask after the employment agreement is in Data/."""
    client = live_client

    uploaded = client.post(
        "/documents/upload",
        files={
            "file": (
                EMPLOYMENT_01.name,
                EMPLOYMENT_01.read_bytes(),
                _content_type(EMPLOYMENT_01),
            )
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()["document"]["document_id"]

    asked = client.post(
        "/ask",
        json={
            "query": "What is the Notice period reference?",
            "document_id": document_id,
        },
    )
    assert asked.status_code == 200, asked.text
    body = asked.json()
    assert body["answer"]
    assert "not present" not in body["answer"].lower()
    assert "calendar days" in body["answer"].lower()
    assert body["source"] == EMPLOYMENT_01.name
    assert body["chunk_id"]
    assert body["supporting_text"]
    assert body["page"] is not None
