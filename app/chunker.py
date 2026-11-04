from dataclasses import dataclass

from app.config import settings
from app.parser import Page


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= size:
        return [text]

    parts = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


def chunk_pages(pages: list[Page], document_id: str) -> list[Chunk]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[Chunk] = []
    index = 0

    for page in pages:
        parts = _split_text(page.text, size, overlap)
        for part in parts:
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}-{index}",
                    document_id=document_id,
                    page_number=page.page_number,
                    chunk_index=index,
                    text=part,
                )
            )
            index += 1
    return chunks
