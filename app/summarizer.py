from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.config import settings
from app.nvidia_client import chat_json
from app.parser import Page


@dataclass
class BatchSummary:
    batch_index: int
    page_start: int
    page_end: int
    summary: str


@dataclass
class DocumentOverview:
    title: str
    short_summary: str
    key_topics: list[str]
    entities: list[str]
    batch_summaries: list[BatchSummary]


def _page_batches(pages: list[Page], size: int) -> list[list[Page]]:
    return [pages[i : i + size] for i in range(0, len(pages), size)]


def _summarize_batch(batch_index: int, batch: list[Page]) -> BatchSummary:
    body = "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in batch)
    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Summarize only facts present in the text. "
                    'Return JSON: {"summary": "..."}'
                ),
            },
            {"role": "user", "content": body[:12000]},
        ],
        max_tokens=400,
    )
    return BatchSummary(
        batch_index=batch_index,
        page_start=batch[0].page_number,
        page_end=batch[-1].page_number,
        summary=str(data.get("summary") or "").strip(),
    )


def summarize_pages(pages: list[Page]) -> DocumentOverview:
    if not pages:
        raise ValueError("No pages to summarize.")

    batches = _page_batches(pages, settings.pages_per_batch)
    workers = max(1, min(settings.max_parallel, len(batches)))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(
                lambda item: _summarize_batch(item[0], item[1]),
                enumerate(batches),
            )
        )

    combined = "\n".join(
        f"Pages {item.page_start}-{item.page_end}: {item.summary}" for item in results
    )
    meta = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Create document metadata from batch summaries. "
                    "Use only information that is present. "
                    'Return JSON: {"title": "...", "short_summary": "...", '
                    '"key_topics": ["..."], "entities": ["..."]}'
                ),
            },
            {"role": "user", "content": combined[:8000]},
        ],
        max_tokens=500,
    )

    topics = meta.get("key_topics") or []
    entities = meta.get("entities") or []
    if not isinstance(topics, list):
        topics = [str(topics)]
    if not isinstance(entities, list):
        entities = [str(entities)]

    return DocumentOverview(
        title=str(meta.get("title") or "").strip(),
        short_summary=str(meta.get("short_summary") or combined).strip(),
        key_topics=[str(item) for item in topics],
        entities=[str(item) for item in entities],
        batch_summaries=results,
    )
