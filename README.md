# Intelligent Document Processing and Semantic Search

Small FastAPI app that takes PDF/TXT files, extracts structured data with an LLM, and answers questions from the uploaded documents (RAG). Answers must come from the files, not from general knowledge.

## What it does

1. Upload a PDF or TXT file.
2. Extract text page by page (PyMuPDF).
3. Summarize pages in batches, classify the document type, then fill a JSON schema.
4. Store metadata and extracted JSON in SQLite.
5. Chunk the text, embed with a local model, store vectors in FAISS.
6. Search and ask questions with source, page, and supporting text.

Document types:

- Employment Agreement
- Company Policy
- Product Documentation
- Project Proposal

## Stack

- API: FastAPI
- LLM: DeepSeek V4.1 Flash on NVIDIA NIM
- Embeddings: `BAAI/bge-base-en-v1.5` (local)
- PDF: PyMuPDF
- DB: SQLite
- Vectors: FAISS

## Run locally (later)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put your NVIDIA API key in `.env` as `NVIDIA_API_KEY`. Do not commit `.env`.

Then (once the API file exists):

```bash
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Current status

Done:

- `requirements.txt`, `.env.example`, `.gitignore`
- `app/config.py` (loads `.env`)

Next: schemas, parser, extraction, search, API, tests.

Config knobs (`CHUNK_SIZE`, `PAGES_PER_BATCH`, etc.) live in `.env`.
