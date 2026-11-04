import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.chunker import chunk_pages
from app.classifier import classify_document
from app.config import settings
from app.database import (
    get_by_hash,
    get_document,
    init_db,
    list_documents,
    new_document_id,
    save_document,
)
from app.embeddings import embed_chunks
from app.extractor import extract_fields
from app.nvidia_client import LLMError
from app.parser import ParseError, extract_pages
from app.rag import ask as rag_ask
from app.rag import search as rag_search
from app.schemas import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.storage import StorageError, save_upload
from app.summarizer import summarize_pages
from app.vectorstore import get_store

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("docintel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database ready")
    yield


app = FastAPI(
    title="Document Intelligence API",
    description="Upload PDF/TXT files, extract structured data, search and ask questions.",
    version="1.0",
    lifespan=lifespan,
)


@app.exception_handler(StorageError)
async def storage_error(_: Request, exc: StorageError):
    logger.warning("Storage error: %s", exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ParseError)
async def parse_error(_: Request, exc: ParseError):
    logger.warning("Parse error: %s", exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(LLMError)
async def llm_error(_: Request, exc: LLMError):
    logger.exception("LLM error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def process_upload(file_name: str, content: bytes):
    saved = save_upload(file_name, content)
    existing = get_by_hash(saved.file_hash)
    if existing:
        logger.info("Duplicate upload skipped: %s", saved.file_name)
        return existing, True

    pages = extract_pages(saved.path)
    overview = summarize_pages(pages)
    doc_type = classify_document(overview.short_summary, overview.title)
    extracted = extract_fields(pages, doc_type)

    document_id = new_document_id()
    record = save_document(
        document_id=document_id,
        file_name=saved.file_name,
        file_type=saved.file_type,
        file_path=saved.path,
        file_hash=saved.file_hash,
        total_pages=len(pages),
        document_type=doc_type.value,
        title=overview.title,
        short_summary=overview.short_summary,
        key_topics=overview.key_topics,
        entities=overview.entities,
        extracted_data=extracted.model_dump(),
    )

    chunks = chunk_pages(pages, document_id)
    vectors = embed_chunks(
        chunks,
        file_name=saved.file_name,
        document_type=doc_type.value,
        title=overview.title,
        short_summary=overview.short_summary,
    )
    get_store().add_chunks(chunks, vectors)
    logger.info("Processed %s as %s (%s)", saved.file_name, doc_type.value, document_id)
    return record, False


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is missing.")
    content = await file.read()
    record, duplicate = process_upload(file.filename, content)
    return {"duplicate": duplicate, "document": record}


@app.get("/documents")
def list_uploaded_documents():
    return list_documents()


@app.get("/documents/{document_id}")
def get_uploaded_document(document_id: str):
    record = get_document(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return record


@app.post("/search", response_model=SearchResponse)
def search_documents(body: SearchRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")
    results = rag_search(
        body.query,
        document_id=body.document_id,
        document_type=body.document_type,
        top_k=body.top_k,
    )
    return SearchResponse(query=body.query, results=results)


@app.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")
    return rag_ask(
        body.query,
        document_id=body.document_id,
        document_type=body.document_type,
    )
