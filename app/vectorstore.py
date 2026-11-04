import json
from dataclasses import dataclass

import faiss
import numpy as np

from app.chunker import Chunk
from app.config import settings


@dataclass
class StoredChunk:
    document_id: str
    chunk_id: str
    text: str
    page_number: int
    score: float | None = None


class VectorStore:
    def __init__(self) -> None:
        self.index: faiss.IndexFlatIP | None = None
        self.items: list[dict] = []
        self._load()

    def _index_path(self):
        return settings.resolve(settings.faiss_index_path)

    def _meta_path(self):
        return settings.resolve(settings.faiss_meta_path)

    def _load(self) -> None:
        index_path = self._index_path()
        meta_path = self._meta_path()
        if index_path.exists() and meta_path.exists():
            self.index = faiss.read_index(str(index_path))
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            self.items = payload.get("items", [])
        else:
            self.index = None
            self.items = []

    def _save(self) -> None:
        if self.index is None:
            return
        index_path = self._index_path()
        meta_path = self._meta_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_path))
        meta_path.write_text(
            json.dumps({"items": self.items}, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def add_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length must match")
        if not chunks:
            return

        matrix = np.array(vectors, dtype="float32")
        if self.index is None:
            self.index = faiss.IndexFlatIP(matrix.shape[1])
        self.index.add(matrix)

        for chunk in chunks:
            self.items.append(
                {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                }
            )
        self._save()

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_id: str | None = None,
    ) -> list[StoredChunk]:
        if self.index is None or not self.items:
            return []

        fetch = min(len(self.items), max(top_k * 8, top_k))
        query = np.array([query_vector], dtype="float32")
        scores, ids = self.index.search(query, fetch)

        hits = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            item = self.items[int(idx)]
            if document_id and item["document_id"] != document_id:
                continue
            hits.append(
                StoredChunk(
                    document_id=item["document_id"],
                    chunk_id=item["chunk_id"],
                    text=item["text"],
                    page_number=item["page_number"],
                    score=float(score),
                )
            )
            if len(hits) >= top_k:
                break
        return hits


_store: VectorStore | None = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def reset_store() -> None:
    global _store
    _store = None
