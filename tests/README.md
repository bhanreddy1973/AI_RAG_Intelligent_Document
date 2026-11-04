# Tests

For the full reviewer walkthrough (manual evaluation scenarios + sample file paths), see **[../TESTING.md](../TESTING.md)**.

Run these from the project root after installing dependencies.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Real sample corpus (assignment ≥5 automated cases)

Uses original files under `TEST_DATA/` and `Data/` (not dummy strings):

```powershell
pytest tests/test_real_corpus.py -v
```

## One file at a time

```powershell
pytest tests/test_real_corpus.py -v
pytest tests/test_config.py -v
pytest tests/test_schemas.py -v
pytest tests/test_parser.py -v
pytest tests/test_parser_data.py -v
pytest tests/test_storage.py -v
pytest tests/test_nvidia_client.py -v
pytest tests/test_summarizer.py -v
pytest tests/test_classifier.py -v
pytest tests/test_extractor.py -v
pytest tests/test_database.py -v
pytest tests/test_chunker.py -v
pytest tests/test_embeddings.py -v
pytest tests/test_vectorstore.py -v
pytest tests/test_rag.py -v
pytest tests/test_api.py -v
```

| Command | What it checks |
|---|---|
| `pytest tests/test_real_corpus.py -v` | Real `TEST_DATA/` + `Data/` parse/chunk/upload cases |
| `pytest tests/test_config.py -v` | `app/config.py` — env defaults and path resolve |
| `pytest tests/test_schemas.py -v` | `app/schemas.py` — document types, Other, Ask/Search shapes |
| `pytest tests/test_parser.py -v` | `app/parser.py` — PDF/TXT pages, empty files, bad types |
| `pytest tests/test_parser_data.py -v` | `app/parser.py` on PDFs in `Data/` |
| `pytest tests/test_storage.py -v` | `app/storage.py` — save, hash, duplicates |
| `pytest tests/test_nvidia_client.py -v` | `app/nvidia_client.py` — key check, retry, JSON parse |
| `pytest tests/test_summarizer.py -v` | `app/summarizer.py` — page batches and metadata |
| `pytest tests/test_classifier.py -v` | `app/classifier.py` — four types plus Other |
| `pytest tests/test_extractor.py -v` | `app/extractor.py` — schema fields, pages, missing/other |
| `pytest tests/test_database.py -v` | `app/database.py` — save, get, hash lookup, list |
| `pytest tests/test_chunker.py -v` | `app/chunker.py` — recursive split, size, overlap, page numbers |
| `pytest tests/test_embeddings.py -v` | `app/embeddings.py` — vectors (model mocked) |
| `pytest tests/test_vectorstore.py -v` | `app/vectorstore.py` — FAISS add/search/filter |
| `pytest tests/test_rag.py -v` | `app/rag.py` — grounded answer and not-found |
| `pytest tests/test_api.py -v` | `app/main.py` — five endpoints, errors, duplicate upload |

## All current tests

```powershell
pytest tests -v
```

## One test only

```powershell
pytest tests/test_parser.py::test_txt_is_page_one -v
```
