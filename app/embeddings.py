from app.chunker import Chunk
from app.config import settings

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    return _model


def build_chunk_embed_text(
    chunk_text: str,
    file_name: str | None = None,
    document_type: str | None = None,
    title: str | None = None,
    short_summary: str | None = None,
) -> str:
    lines = []
    if file_name:
        lines.append(f"Document: {file_name}")
    if document_type:
        lines.append(f"Type: {document_type}")
    if title:
        lines.append(f"Title: {title}")
    if short_summary:
        lines.append(f"Context: {short_summary}")
    lines.append(chunk_text)
    return "\n".join(lines)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def embed_chunks(
    chunks: list[Chunk],
    file_name: str | None = None,
    document_type: str | None = None,
    title: str | None = None,
    short_summary: str | None = None,
) -> list[list[float]]:
    texts = [
        build_chunk_embed_text(
            chunk.text,
            file_name=file_name,
            document_type=document_type,
            title=title,
            short_summary=short_summary,
        )
        for chunk in chunks
    ]
    return embed_texts(texts)


def embed_query(text: str) -> list[float]:
    vectors = embed_texts([text])
    return vectors[0]
