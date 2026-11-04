from app.database import get_by_hash, get_document, list_documents, save_document


def _save(tmp_path, monkeypatch, file_hash="abc123", name="a.pdf"):
    monkeypatch.setattr("app.database.settings.sqlite_path", str(tmp_path / "app.db"))
    return save_document(
        document_id="doc-1",
        file_name=name,
        file_type="pdf",
        file_path=tmp_path / name,
        file_hash=file_hash,
        total_pages=4,
        document_type="Employment Agreement",
        title="Employment Agreement",
        short_summary="Notice period is 60 days.",
        key_topics=["Termination"],
        entities=["ABC Technologies"],
        extracted_data={"notice_period": {"value": "60 days", "page": 4}},
    )


def test_save_and_get_document(tmp_path, monkeypatch):
    saved = _save(tmp_path, monkeypatch)
    loaded = get_document("doc-1")

    assert saved.document_id == "doc-1"
    assert loaded is not None
    assert loaded.file_metadata.file_name == "a.pdf"
    assert loaded.document_metadata.document_type == "Employment Agreement"
    assert loaded.extracted_data["notice_period"]["value"] == "60 days"
    assert loaded.processing_metadata.status == "completed"


def test_get_by_hash_finds_duplicate(tmp_path, monkeypatch):
    _save(tmp_path, monkeypatch, file_hash="same-hash")
    found = get_by_hash("same-hash")
    missing = get_by_hash("other-hash")

    assert found is not None
    assert found.document_id == "doc-1"
    assert missing is None


def test_list_documents(tmp_path, monkeypatch):
    _save(tmp_path, monkeypatch)
    items = list_documents()
    assert len(items) == 1
    assert items[0].file_name == "a.pdf"
    assert items[0].status == "completed"
