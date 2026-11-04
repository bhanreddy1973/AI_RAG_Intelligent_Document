# Tests

Run these from the project root after installing dependencies.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## One file at a time

```powershell
pytest tests/test_config.py -v
pytest tests/test_schemas.py -v
pytest tests/test_parser.py -v
pytest tests/test_parser_data.py -v
```

| Command | What it checks |
|---|---|
| `pytest tests/test_config.py -v` | `app/config.py` — env defaults and path resolve |
| `pytest tests/test_schemas.py -v` | `app/schemas.py` — document types, Other, Ask/Search shapes |
| `pytest tests/test_parser.py -v` | `app/parser.py` — PDF/TXT pages, empty files, bad types |
| `pytest tests/test_parser_data.py -v` | `app/parser.py` on PDFs in `Data/` |

## All current tests

```powershell
pytest tests -v
```

## One test only

```powershell
pytest tests/test_parser.py::test_txt_is_page_one -v
```
