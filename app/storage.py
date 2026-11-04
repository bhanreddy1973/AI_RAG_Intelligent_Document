import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


class StorageError(Exception):
    pass


@dataclass
class SavedFile:
    path: Path
    file_hash: str
    file_name: str
    file_type: str
    is_duplicate: bool


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_upload(file_name: str, content: bytes) -> SavedFile:
    if not content:
        raise StorageError("Uploaded file is empty.")

    suffix = Path(file_name).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise StorageError(f"Unsupported file type: {suffix or 'unknown'}. Use PDF or TXT.")

    digest = file_hash(content)
    upload_dir = settings.resolve(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / f"{digest}{suffix}"
    already_there = dest.exists()
    if not already_there:
        dest.write_bytes(content)

    return SavedFile(
        path=dest,
        file_hash=digest,
        file_name=Path(file_name).name,
        file_type=suffix.lstrip("."),
        is_duplicate=already_there,
    )
