from app.config import settings
from app.database import get_document
from app.embeddings import embed_query
from app.nvidia_client import chat_json
from app.schemas import AskResponse, SearchHit
from app.vectorstore import StoredChunk, get_store


NOT_FOUND = "This information is not present in the uploaded documents."


def _file_name(document_id: str) -> str:
    record = get_document(document_id)
    if record is None:
        return document_id
    return record.file_metadata.file_name


def _document_type(document_id: str) -> str | None:
    record = get_document(document_id)
    if record is None:
        return None
    return record.document_metadata.document_type


def _to_hit(hit: StoredChunk) -> SearchHit:
    return SearchHit(
        document_id=hit.document_id,
        file_name=_file_name(hit.document_id),
        page=hit.page_number,
        chunk_id=hit.chunk_id,
        score=hit.score or 0.0,
        text=hit.text,
    )


def search(
    query: str,
    document_id: str | None = None,
    document_type: str | None = None,
    top_k: int | None = None,
) -> list[SearchHit]:
    k = top_k or settings.top_k
    fetch = k * 8 if document_type else k
    vector = embed_query(query)
    hits = get_store().search(vector, top_k=fetch, document_id=document_id)

    results = []
    for hit in hits:
        if document_type and _document_type(hit.document_id) != document_type:
            continue
        results.append(_to_hit(hit))
        if len(results) >= k:
            break
    return results


def ask(
    query: str,
    document_id: str | None = None,
    document_type: str | None = None,
) -> AskResponse:
    hits = search(query, document_id=document_id, document_type=document_type)
    if not hits or hits[0].score < settings.min_score:
        return AskResponse(answer=NOT_FOUND)

    context = "\n\n".join(
        f"[{item.chunk_id}] {item.file_name} page {item.page}: {item.text}"
        for item in hits
    )
    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Answer only from the context. If the answer is not in the context, "
                    f'say "{NOT_FOUND}". '
                    'Return JSON: {"answer": "...", "chunk_id": "..."}'
                ),
            },
            {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
        ],
        max_tokens=400,
    )

    answer = str(data.get("answer") or "").strip()
    if not answer or NOT_FOUND.lower() in answer.lower():
        return AskResponse(answer=NOT_FOUND)

    chosen = hits[0]
    wanted = data.get("chunk_id")
    if wanted:
        for item in hits:
            if item.chunk_id == wanted:
                chosen = item
                break

    return AskResponse(
        answer=answer,
        source=chosen.file_name,
        page=chosen.page,
        chunk_id=chosen.chunk_id,
        supporting_text=chosen.text,
    )
