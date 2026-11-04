from dataclasses import dataclass

from app.config import settings
from app.parser import Page

# Prefer larger semantic breaks first, then fall back to finer ones.
SEPARATORS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", "")


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str


def _split_keep_separator(text: str, separator: str) -> list[str]:
    if separator == "":
        return list(text)

    parts = text.split(separator)
    if len(parts) == 1:
        return parts

    units: list[str] = []
    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            units.append(part + separator)
        elif part:
            units.append(part)
    return [unit for unit in units if unit]


def _recursive_split(text: str, separators: list[str], size: int) -> list[str]:
    if not text:
        return []
    if len(text) <= size:
        return [text]

    separator = separators[-1]
    next_separators: list[str] = []
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = ""
            next_separators = []
            break
        if candidate in text:
            separator = candidate
            next_separators = separators[index + 1 :]
            break

    units: list[str] = []
    for piece in _split_keep_separator(text, separator):
        if len(piece) <= size:
            units.append(piece)
            continue
        if next_separators:
            units.extend(_recursive_split(piece, next_separators, size))
        else:
            # Last resort: hard character windows (no mid-unit merge).
            for start in range(0, len(piece), size):
                units.append(piece[start : start + size])
    return units


def _start_next_chunk(previous: str, unit: str, size: int, overlap: int) -> str:
    # Do not carry overlap across paragraph boundaries.
    if previous.endswith("\n\n") or overlap <= 0:
        return unit
    tail = previous[-overlap:]
    if len(tail) + len(unit) <= size:
        return tail + unit
    return unit


def _merge_with_overlap(units: list[str], size: int, overlap: int) -> list[str]:
    if not units:
        return []

    chunks: list[str] = []
    current = ""

    for unit in units:
        if not current:
            current = unit
            continue

        # Keep paragraph breaks intact instead of filling leftover space
        # with the start of the next paragraph.
        if current.endswith("\n\n"):
            chunks.append(current.strip())
            current = _start_next_chunk(current, unit, size, overlap)
            continue

        if len(current) + len(unit) <= size:
            current += unit
            continue

        chunks.append(current.strip())
        current = _start_next_chunk(current, unit, size, overlap)

    if current.strip():
        chunks.append(current.strip())
    return chunks


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    units = _recursive_split(text, list(SEPARATORS), size)
    return _merge_with_overlap(units, size, overlap)


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
