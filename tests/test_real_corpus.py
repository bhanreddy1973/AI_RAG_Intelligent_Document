"""Automated cases using real sample files and real app storage paths.

These tests hit the real FastAPI endpoints and write to the configured
Data/ SQLite + FAISS locations (from .env). LLM and embeddings are NOT mocked.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.chunker import chunk_pages
from app.config import ROOT_DIR, settings
from app.parser import extract_pages
from app.vectorstore import reset_store

TEST_DATA = ROOT_DIR / "TEST_DATA"
DATA_DIR = ROOT_DIR / "Data"

EMPLOYMENT_01 = TEST_DATA / "employment_agreement_01.txt"
POLICY_01 = TEST_DATA / "company_policy_01.txt"
PRODUCT_01 = TEST_DATA / "product_documentation_01.txt"
TECH_01 = TEST_DATA / "technical_specification_01.txt"
TEMPLATE_PDF = DATA_DIR / "Template_Employment_Agreement.pdf"


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


@pytest.fixture
def live_client():
    """Use real SQLITE_PATH / UPLOAD_DIR / FAISS paths from settings (.env)."""
    _require_live_llm()
    reset_store()
    from app.main import app

    with TestClient(app) as client:
        yield client
    reset_store()


def test_1_real_employment_txt_parses():
    """Real path: TEST_DATA/employment_agreement_01.txt"""
    assert EMPLOYMENT_01.is_file()
    pages = extract_pages(EMPLOYMENT_01)
    text = "\n".join(page.text for page in pages)

    assert len(pages) >= 1
    assert pages[0].page_number == 1
    assert "Mira Deshpande" in text
    assert "Northstar Analytics" in text
    assert "notice period" in text.lower()


def test_2_real_company_policy_txt_parses():
    """Real path: TEST_DATA/company_policy_01.txt"""
    assert POLICY_01.is_file()
    pages = extract_pages(POLICY_01)
    text = "\n".join(page.text for page in pages)

    assert "Cedarline Technologies" in text
    assert "Nisha Kulkarni" in text
    assert "POL-03-201" in text


def test_3_real_employment_chunks_keep_notice_period():
    """Real path: TEST_DATA/employment_agreement_01.txt — recursive chunking keeps facts."""
    pages = extract_pages(EMPLOYMENT_01)
    chunks = chunk_pages(pages, document_id="real-emp-01")

    assert len(chunks) >= 2
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert any("notice period" in chunk.text.lower() for chunk in chunks)
    assert chunks[0].chunk_id == "real-emp-01-0"


def test_4_real_product_and_technical_txt_parse():
    """Real paths: product_documentation_01.txt and technical_specification_01.txt"""
    assert PRODUCT_01.is_file()
    assert TECH_01.is_file()

    product_pages = extract_pages(PRODUCT_01)
    tech_pages = extract_pages(TECH_01)
    product_text = "\n".join(page.text for page in product_pages)
    tech_text = "\n".join(page.text for page in tech_pages)

    assert "LedgerFlow" in product_text
    assert "Meridian Identity Service" in tech_text or "MIS-310" in tech_text


@pytest.mark.skipif(not TEMPLATE_PDF.is_file(), reason="Data/Template_Employment_Agreement.pdf missing")
def test_5_real_pdf_from_data_parses():
    """Real path: Data/Template_Employment_Agreement.pdf"""
    pages = extract_pages(TEMPLATE_PDF)

    assert len(pages) >= 1
    assert [page.page_number for page in pages] == list(range(1, len(pages) + 1))
    assert any(page.text.strip() for page in pages)


def test_6_api_upload_real_employment_and_policy(live_client):
    """
    Live paths:
    - files: TEST_DATA/employment_agreement_01.txt, company_policy_01.txt
    - storage: Data/app.db, Data/uploads, Data/faiss.*
    - endpoints: POST /documents/upload, GET /documents, GET /documents/{id}, POST /search
    LLM + local embeddings run for real (not mocked).
    """
    client = live_client

    emp = client.post(
        "/documents/upload",
        files={"file": (EMPLOYMENT_01.name, EMPLOYMENT_01.read_bytes(), "text/plain")},
    )
    pol = client.post(
        "/documents/upload",
        files={"file": (POLICY_01.name, POLICY_01.read_bytes(), "text/plain")},
    )

    assert emp.status_code == 200, emp.text
    assert pol.status_code == 200, pol.text

    emp_body = emp.json()["document"]
    pol_body = pol.json()["document"]

    assert emp_body["file_metadata"]["file_name"] == EMPLOYMENT_01.name
    assert pol_body["file_metadata"]["file_name"] == POLICY_01.name
    assert emp_body["document_metadata"]["document_type"]
    assert pol_body["document_metadata"]["document_type"]
    assert emp_body["extracted_data"]
    assert pol_body["extracted_data"]

    # Confirm writes landed on real Data/ paths from .env
    assert settings.resolve(settings.sqlite_path).exists()
    assert settings.resolve(settings.upload_dir).exists()
    assert settings.resolve(settings.faiss_index_path).exists()
    assert settings.resolve(settings.faiss_meta_path).exists()

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    detail = client.get(f"/documents/{emp_body['document_id']}")
    assert detail.status_code == 200
    assert detail.json()["document_id"] == emp_body["document_id"]

    search = client.post(
        "/search",
        json={
            "query": "notice period",
            "document_id": emp_body["document_id"],
            "top_k": 3,
        },
    )
    assert search.status_code == 200, search.text
    assert search.json()["results"]


def test_7_api_ask_real_notice_period(live_client):
    """
    Live POST /ask against documents already in Data/ (uploads if needed).
    Expects a grounded answer with source references when notice period exists.
    """
    client = live_client

    # Ensure employment file is present (idempotent if duplicate hash exists).
    uploaded = client.post(
        "/documents/upload",
        files={"file": (EMPLOYMENT_01.name, EMPLOYMENT_01.read_bytes(), "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()["document"]["document_id"]

    asked = client.post(
        "/ask",
        json={
            "query": "What is the notice period in the employment agreement?",
            "document_id": document_id,
        },
    )
    assert asked.status_code == 200, asked.text
    body = asked.json()
    assert body["answer"]
    assert "not present" not in body["answer"].lower()
    assert body["source"]
    assert body["chunk_id"]
    assert body["supporting_text"]
