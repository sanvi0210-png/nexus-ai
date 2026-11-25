from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    # Loaded on first use so the API starts fast. Downloads once, then runs locally.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
