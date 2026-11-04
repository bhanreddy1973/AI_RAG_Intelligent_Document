from app.config import settings

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def embed_query(text: str) -> list[float]:
    vectors = embed_texts([text])
    return vectors[0]
