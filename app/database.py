import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.schemas import (
    DocumentListItem,
    DocumentMetadata,
    DocumentRecord,
    FileMetadata,
    ProcessingMetadata,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    path = settings.resolve(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                total_pages INTEGER NOT NULL,
                document_type TEXT,
                title TEXT,
                short_summary TEXT,
                key_topics TEXT,
                entities TEXT,
                processing_status TEXT NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extracted_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                extracted_json TEXT NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0',
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(document_id)
            );
            """
        )


def new_document_id() -> str:
    return str(uuid.uuid4())


def get_by_hash(file_hash: str) -> DocumentRecord | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE file_hash = ?",
            (file_hash,),
        ).fetchone()
        if row is None:
            return None
        extracted = conn.execute(
            "SELECT extracted_json, schema_version FROM extracted_documents WHERE document_id = ?",
            (row["document_id"],),
        ).fetchone()
        return _to_record(row, extracted)


def save_document(
    *,
    document_id: str,
    file_name: str,
    file_type: str,
    file_path: str | Path,
    file_hash: str,
    total_pages: int,
    document_type: str,
    title: str | None,
    short_summary: str | None,
    key_topics: list[str],
    entities: list[str],
    extracted_data: dict,
    status: str = "completed",
    schema_version: str = "1.0",
) -> DocumentRecord:
    init_db()
    created_at = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO documents (
                document_id, file_name, file_type, file_path, file_hash,
                total_pages, document_type, title, short_summary, key_topics,
                entities, processing_status, schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                file_name,
                file_type,
                str(file_path),
                file_hash,
                total_pages,
                document_type,
                title,
                short_summary,
                json.dumps(key_topics),
                json.dumps(entities),
                status,
                schema_version,
                created_at,
            ),
        )
        conn.execute(
            """
            INSERT INTO extracted_documents (
                document_id, extracted_json, schema_version, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (document_id, json.dumps(extracted_data), schema_version, created_at),
        )
    record = get_document(document_id)
    if record is None:
        raise RuntimeError("Failed to load saved document.")
    return record


def get_document(document_id: str) -> DocumentRecord | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        if row is None:
            return None
        extracted = conn.execute(
            "SELECT extracted_json, schema_version FROM extracted_documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        return _to_record(row, extracted)


def list_documents() -> list[DocumentListItem]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT document_id, file_name, document_type, created_at, processing_status
            FROM documents
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [
        DocumentListItem(
            document_id=row["document_id"],
            file_name=row["file_name"],
            document_type=row["document_type"],
            uploaded_at=datetime.fromisoformat(row["created_at"]),
            status=row["processing_status"],
        )
        for row in rows
    ]


def _to_record(row: sqlite3.Row, extracted: sqlite3.Row | None) -> DocumentRecord:
    extracted_data = {}
    schema_version = row["schema_version"]
    if extracted is not None:
        extracted_data = json.loads(extracted["extracted_json"])
        schema_version = extracted["schema_version"]
    return DocumentRecord(
        document_id=row["document_id"],
        file_metadata=FileMetadata(
            file_name=row["file_name"],
            file_type=row["file_type"],
            file_hash=row["file_hash"],
            total_pages=row["total_pages"],
            uploaded_at=datetime.fromisoformat(row["created_at"]),
        ),
        document_metadata=DocumentMetadata(
            document_type=row["document_type"] or "Other",
            title=row["title"],
            short_summary=row["short_summary"],
            key_topics=json.loads(row["key_topics"] or "[]"),
            entities=json.loads(row["entities"] or "[]"),
        ),
        extracted_data=extracted_data,
        processing_metadata=ProcessingMetadata(
            status=row["processing_status"],
            schema_version=schema_version,
        ),
    )
