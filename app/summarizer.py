import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.config import settings
from app.nvidia_client import LLMError, chat_json
from app.parser import Page

logger = logging.getLogger("docintel")


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


def _fallback_summary(batch: list[Page]) -> str:
    text = " ".join(page.text for page in batch)
    text = " ".join(text.split())
    if not text:
        return "No readable text in these pages."
    return text[:500]


def _summarize_batch(batch_index: int, batch: list[Page]) -> BatchSummary:
    body = "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in batch)
    try:
        data = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Summarize only facts present in the text. "
                        "Keep the summary to 1-2 short sentences. "
                        'Return JSON only: {"summary": "..."}'
                    ),
                },
                {"role": "user", "content": body[:8000]},
            ],
            max_tokens=300,
        )
        summary = str(data.get("summary") or "").strip()
        if not summary:
            summary = _fallback_summary(batch)
    except LLMError as exc:
        # Large PDFs make many batch calls; one bad JSON reply must not fail upload.
        logger.warning(
            "Batch %s summary failed (%s). Using text fallback.",
            batch_index,
            exc,
        )
        summary = _fallback_summary(batch)

    return BatchSummary(
        batch_index=batch_index,
        page_start=batch[0].page_number,
        page_end=batch[-1].page_number,
        summary=summary,
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
                    "Keep short_summary to 2-3 sentences. "
                    "Return JSON only: "
                    '{"title": "...", "short_summary": "...", '
                    '"key_topics": ["..."], "entities": ["..."]}'
                ),
            },
            {"role": "user", "content": combined[:8000]},
        ],
        max_tokens=700,
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
