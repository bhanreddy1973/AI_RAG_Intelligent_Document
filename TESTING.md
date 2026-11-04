# Testing Guide

This document explains how to verify the Intelligent Document Processing & Semantic Search system: environment setup, sample data paths, **manual evaluation scenarios**, and **automated pytest** coverage.

All paths below are **relative to the project root**.

---

## 1. Prerequisites

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

1. Put a valid NVIDIA NIM key in `.env` as `NVIDIA_API_KEY` (do not commit `.env`).
2. Confirm:
   - `LLM_PROVIDER=nvidia`
   - `NVIDIA_LLM_MODEL=nvidia/nemotron-3-ultra-550b-a55b` (or another working NIM chat model)
3. Start the API:

```powershell
uvicorn app.main:app --reload
```

4. Open Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Notes**

- First embedding model download (`BAAI/bge-base-en-v1.5`) can take several minutes.
- Large PDFs (100+ pages) take longer because summarize/classify/extract call the LLM many times.
- `document_id` and `document_type` on `/search` and `/ask` are **optional**. Only `query` is required.

---

## 2. Sample data

### 2.1 Synthetic corpus — `TEST_DATA/`

| Relative path | Suggested type | Useful facts for Q&A |
|---|---|---|
| `TEST_DATA/employment_agreement_01.txt` | Employment Agreement | Employee Mira Deshpande; Northstar Analytics; notice periods (30/45/60 days in sections); salary examples |
| `TEST_DATA/employment_agreement_02.txt` | Employment Agreement | Second employment variant |
| `TEST_DATA/company_policy_01.txt` | Company Policy | Cedarline Technologies; policy owner Nisha Kulkarni; POL-03-* controls; eligibility |
| `TEST_DATA/company_policy_02.txt` | Company Policy | Second policy variant |
| `TEST_DATA/product_documentation_01.txt` | Product Documentation | LedgerFlow 2.7.1 product overview |
| `TEST_DATA/product_documentation_02.txt` | Product Documentation | Second product variant |
| `TEST_DATA/technical_specification_01.txt` | Other / technical | Meridian Identity Service (MIS-310) |
| `TEST_DATA/technical_specification_02.txt` | Other / technical | Second technical variant |

These TXT files are fictional synthetic documents prepared for ingestion, classification, extraction, chunking, and RAG testing.

### 2.2 Real / larger samples — `Data/`

| Relative path | Format | Notes |
|---|---|---|
| `Data/Company-Policy-and-Procedure-June-1.18-V6.0.pdf` | PDF | Large multi-page company policy (~100+ pages). Good PDF end-to-end test. |
| `Data/EMPLOYMENT_AGREEMENT (3).pdf` | PDF | Employment agreement PDF |
| `Data/Template_Employment_Agreement.pdf` | PDF | Employment agreement template |
| `Data/policy-and-procedure-workbook-update.pdf` | PDF | Policy / procedure workbook |
| `Data/Pexip_Infinity_Release_Notes_v42(product).a.pdf` | PDF | Product release notes |
| `Data/Slides-Methods3-Faiferlick-User-Documentation(product).pdf` | PDF | Product / user documentation |
| `Data/document_test_corpus_8_files.zip` | ZIP | Archive of the 8 synthetic TXT files (same family as `TEST_DATA/`) |

**Runtime artifacts (not input fixtures)** — created while the app runs; safe to ignore or delete between clean demos:

- `Data/app.db`
- `Data/faiss.index`
- `Data/faiss_meta.json`
- `Data/uploads/`

---

## 3. Manual test cases (assignment evaluation scenarios)

Use Swagger or `curl`. After each upload, copy `document_id` from the response if you want filtered ask/search.

### M1 — Upload two documents and retrieve metadata

**Requirement:** Upload two different documents and retrieve their metadata.

**Steps**

1. `POST /documents/upload` with `TEST_DATA/employment_agreement_01.txt`
2. `POST /documents/upload` with `TEST_DATA/company_policy_01.txt`
3. `GET /documents` — expect at least two entries with different `document_id` values
4. `GET /documents/{id}` for each id

**Pass criteria**

- HTTP 200 on all calls
- `processing_metadata.status` is `completed`
- `document_metadata.document_type` looks correct (Employment Agreement / Company Policy)
- `extracted_data` is present with `{value, page}` fields
- Optional PDF variant: also upload `Data/Template_Employment_Agreement.pdf` and confirm `file_type` is `pdf` and `total_pages` > 1

---

### M2 — Question whose answer exists in the document

**Requirement:** Ask a question whose answer exists in the document.

**Steps**

1. Upload `TEST_DATA/employment_agreement_01.txt` if not already present
2. `POST /ask` with body:

```json
{
  "query": "What notice period values are mentioned for Mira Deshpande?"
}
```

(Optional filter) add `"document_id": "<id from upload>"`.

**Pass criteria**

- Answer mentions a notice period grounded in the file (e.g. 30 / 45 / 60 calendar days)
- `source`, `page`, `chunk_id`, and `supporting_text` are non-null
- Supporting text appears in the uploaded document

---

### M3 — Question whose answer does **not** exist

**Requirement:** Ask a question whose answer does not exist in the document.

**Steps**

1. `POST /ask`:

```json
{
  "query": "What is the CEO's exact USD salary bank account number?"
}
```

**Pass criteria**

- Answer is the not-found message: *This information is not present in the uploaded documents.*
- `source`, `page`, and `chunk_id` are null (no invented account number)

---

### M4 — Retrieval across multiple documents

**Requirement:** Ask a question requiring retrieval from multiple documents.

**Steps**

1. Ensure both an employment and a policy file are uploaded (M1)
2. `POST /ask` **without** `document_id`:

```json
{
  "query": "Which uploaded documents mention remote work, WFH, or managed laptops?"
}
```

3. Also try `POST /search`:

```json
{
  "query": "remote work managed laptops policy",
  "top_k": 5
}
```

**Pass criteria**

- Search hits can come from more than one `file_name` / `document_id` when relevant text exists in both corpora
- Ask answer stays grounded and cites a real source when confident

---

### M5 — Same question, different wording

**Requirement:** Ask the same question using different wording.

**Steps**

1. Restrict to the employment document id from M1
2. Ask:

```json
{"query": "What is the notice period?", "document_id": "<employment_id>"}
```

3. Ask again:

```json
{"query": "How many days of advance notice must the employee give before leaving?", "document_id": "<employment_id>"}
```

**Pass criteria**

- Both answers refer to the same underlying fact(s) from the employment file
- Both include valid source references

---

### M6 — Incomplete / inconsistent information

**Requirement:** Upload a document containing incomplete or inconsistent information.

**Steps**

1. Create a tiny local file, e.g. `Data/incomplete_policy.txt`, with:

```text
Company Policy
This draft has no effective date and does not list an owner.
```

2. `POST /documents/upload` that file
3. `GET /documents/{id}`

**Pass criteria**

- Upload succeeds
- Typed fields that are absent remain `null` or appear under `missing_fields`
- No fabricated effective date / owner inventing details not in the text

---

### M7 — Simulate LLM API failure

**Requirement:** Simulate an LLM API failure.

**Preferred (automated, no live key abuse):**

```powershell
pytest tests/test_api.py::test_llm_failure_returns_502 -v
pytest tests/test_nvidia_client.py::test_chat_raises_after_retries -v
```

**Optional live check:** temporarily set a bad `NVIDIA_API_KEY` in `.env`, restart uvicorn, upload any small TXT, expect **502**, then restore the key.

**Pass criteria**

- Failure is handled (HTTP 502 / `LLMError` path), not an uncaught 500 crash
- Automated tests above pass

---

### M8 — Answers contain valid source references

**Requirement:** Verify returned answers contain valid source references.

**Steps**

1. Use a successful `/ask` from M2
2. Confirm `source` equals the uploaded file name
3. Confirm `supporting_text` is a substring (or clear paraphrase span) of content in that file
4. Confirm `chunk_id` looks like `{document_id}-{index}`

**Pass criteria**

- No orphan sources for successful answers
- Not-found answers leave source fields null

---

### M9 — PDF end-to-end (recommended)

**Steps**

1. `POST /documents/upload` with `Data/Company-Policy-and-Procedure-June-1.18-V6.0.pdf`  
   (large file — allow several minutes)
2. `GET /documents/{id}` — check type/summary/extraction
3. `POST /ask`:

```json
{
  "query": "What company issued this policy manual?"
}
```

**Pass criteria**

- HTTP 200, `file_type` = `pdf`, `total_pages` > 1
- Ask returns grounded answer with source pointing at the PDF file name

**Faster PDF alternative:** `Data/Template_Employment_Agreement.pdf`

---

### M10 — Semantic search only (no LLM answer)

**Steps**

1. `POST /search`:

```json
{
  "query": "notice period calendar days",
  "top_k": 3
}
```

**Pass criteria**

- Returns ranked chunks with `score`, `text`, `file_name`, `page`, `chunk_id`
- Does not require an LLM completion for the search path itself

---

### Suggested quick demo script (Swagger)

1. Upload `TEST_DATA/employment_agreement_01.txt`
2. Upload `TEST_DATA/company_policy_01.txt`
3. `GET /documents`
4. `/ask` notice-period question (exists)
5. `/ask` CEO bank account question (does not exist)
6. `/search` remote work (multi-doc)
7. Upload one PDF from `Data/`

---

## 4. Automated test cases

Automated tests live under `tests/`. **Assignment minimum (≥5)** is covered by `tests/test_real_corpus.py`.

All **five** sample files run the **full live pipeline** (upload → LLM extract → embed → FAISS → list/get/search). Storage is the real `.env` `Data/` paths. LLM and embeddings are **not** mocked. Expect several minutes.

Files covered:

1. `TEST_DATA/employment_agreement_01.txt`
2. `TEST_DATA/company_policy_01.txt`
3. `TEST_DATA/product_documentation_01.txt`
4. `TEST_DATA/technical_specification_01.txt`
5. `Data/Template_Employment_Agreement.pdf`

Other modules (`test_api.py`, etc.) still mock LLM/embeddings for fast offline unit coverage.

### 4.1 Run the real-sample automated suite (≥5 cases)

Needs a valid API key in `.env` for your `LLM_PROVIDER`.

```powershell
.\.venv\Scripts\activate
pytest tests/test_real_corpus.py -v
```

| # | Test | What it checks |
|---|---|---|
| 1 | `test_1_corpus_files_exist` | All five sample paths are on disk |
| 2 | `test_2_upload_all_five_full_pipeline` | Live upload of all five → extract/embed → `GET /documents` has all five → get + search each |
| 3 | `test_3_ask_notice_period_on_employment` | Live `/ask` with source / page / chunk refs |

### 4.2 Run all tests

```powershell
pytest tests -v
```

`test_real_corpus.py` is slow (live LLM). For a fast offline run of everything else:

```powershell
pytest tests --ignore=tests/test_real_corpus.py -v
```

### 4.3 Other useful modules

```powershell
pytest tests/test_api.py -v
pytest tests/test_rag.py -v
pytest tests/test_parser_data.py -v
```

`tests/test_parser_data.py` parametrizes over every `Data/*.pdf` present locally. If no PDFs are present, those cases are skipped.

### 4.3 Mapping to assignment requirements

| Requirement area | Automated coverage | Key files / tests |
|---|---|---|
| A. PDF/TXT ingestion, empty/invalid files | Yes | `tests/test_parser.py`, `tests/test_storage.py`, `tests/test_parser_data.py` (`Data/*.pdf`) |
| A. Chunking + page / chunk ids | Yes | `tests/test_chunker.py` |
| B. Schema + missing fields + other_fields | Yes | `tests/test_schemas.py`, `tests/test_extractor.py` |
| B. Malformed LLM JSON / retries | Yes | `tests/test_nvidia_client.py` (`parse_json`, retries) |
| C. Embeddings + FAISS search | Yes | `tests/test_embeddings.py`, `tests/test_vectorstore.py` |
| C. RAG grounded answer + sources | Yes | `tests/test_rag.py::test_ask_returns_source_from_context` |
| C. No relevant results / low score | Yes | `tests/test_rag.py::test_ask_not_found_when_score_is_low` |
| D. Five REST endpoints | Yes | `tests/test_api.py` (upload, list, get, search, ask) |
| E. Invalid file / empty file | Yes | `tests/test_api.py::test_invalid_file_type`, `test_empty_file` |
| E. LLM failure → 502 | Yes | `tests/test_api.py::test_llm_failure_returns_502` |
| E. Empty query | Yes | `tests/test_api.py::test_ask_empty_query` |
| Duplicate upload | Yes | `tests/test_api.py::test_duplicate_upload_is_skipped` |
| Metadata DB | Yes | `tests/test_database.py` |
| Summarizer batching + JSON failure fallback | Yes | `tests/test_summarizer.py` |
| Classifier + Other fallback | Yes | `tests/test_classifier.py` |
| Config / env | Yes | `tests/test_config.py` |

### 4.4 Full per-file checklist

| Command | What it verifies |
|---|---|
| `pytest tests/test_real_corpus.py -v` | **Real `TEST_DATA/` + `Data/` samples (assignment ≥5)** |
| `pytest tests/test_config.py -v` | Env defaults, path resolve |
| `pytest tests/test_schemas.py -v` | Document types, optional search filters, Ask shapes |
| `pytest tests/test_parser.py -v` | PDF/TXT pages, empty/bad types |
| `pytest tests/test_parser_data.py -v` | Live parse of PDFs under `Data/` |
| `pytest tests/test_storage.py -v` | Save, hash, duplicates, rejects |
| `pytest tests/test_nvidia_client.py -v` | Missing key, retry, JSON parse |
| `pytest tests/test_summarizer.py -v` | Batch summaries; fallback when JSON fails |
| `pytest tests/test_classifier.py -v` | Known types + Other |
| `pytest tests/test_extractor.py -v` | Schema fill, pages, missing/other |
| `pytest tests/test_database.py -v` | Save/get/list/hash |
| `pytest tests/test_chunker.py -v` | Size, overlap, page numbers |
| `pytest tests/test_embeddings.py -v` | Vectors + metadata-aware embed text |
| `pytest tests/test_vectorstore.py -v` | FAISS add/search/filter |
| `pytest tests/test_rag.py -v` | Grounded ask + not-found |
| `pytest tests/test_api.py -v` | Endpoints, errors, duplicate, LLM 502 |

More short notes: [tests/README.md](tests/README.md)

---

## 5.  pass/fail summary

| # | Scenario | How to run | Pass if |
|---|---|---|---|
| M1 | Two uploads + metadata | Manual Swagger | Types + extracted JSON present |
| M2 | Answer exists | Manual `/ask` | Answer + source/page/chunk |
| M3 | Answer missing | Manual `/ask` | Not-found, no hallucination |
| M4 | Multi-document | Manual `/ask` + `/search` | Cross-file retrieval possible |
| M5 | Paraphrase | Manual `/ask` ×2 | Same grounded fact |
| M6 | Incomplete doc | Manual upload | Nulls / `missing_fields`, no inventing |
| M7 | LLM failure | `pytest` API/client tests | 502 / clean failure |
| M8 | Source refs | Inspect `/ask` JSON | Valid file/page/chunk |
| Auto | Full suite | `pytest tests -v` | All green |

---

## 6. External services used

| Service | Purpose |
|---|---|
| NVIDIA NIM (`integrate.api.nvidia.com`) | Chat LLM for summarize / classify / extract / ask |
| Local `sentence-transformers` + Hugging Face model hub | First-time download of `BAAI/bge-base-en-v1.5` |

Optional alternates via `LLM_PROVIDER`: `openai`, `gemini`.
