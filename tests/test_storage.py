import hashlib

import pytest

from app.storage import StorageError, file_hash, save_upload


def test_file_hash_is_sha256():
    content = b"hello"
    assert file_hash(content) == hashlib.sha256(content).hexdigest()


def test_save_upload_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.settings.upload_dir", str(tmp_path))
    content = b"notice period 60 days"

    saved = save_upload("agreement.txt", content)

    assert saved.is_duplicate is False
    assert saved.file_name == "agreement.txt"
    assert saved.file_type == "txt"
    assert saved.path.exists()
    assert saved.path.read_bytes() == content
    assert saved.path.name.startswith(saved.file_hash)


def test_same_content_is_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.settings.upload_dir", str(tmp_path))
    content = b"same file twice"

    first = save_upload("a.txt", content)
    second = save_upload("b.txt", content)

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert first.file_hash == second.file_hash
    assert first.path == second.path
    assert len(list(tmp_path.glob("*.txt"))) == 1


def test_empty_upload_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.settings.upload_dir", str(tmp_path))
    with pytest.raises(StorageError, match="empty"):
        save_upload("empty.txt", b"")


def test_unsupported_type_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.settings.upload_dir", str(tmp_path))
    with pytest.raises(StorageError, match="Unsupported file type"):
        save_upload("notes.docx", b"not allowed")
