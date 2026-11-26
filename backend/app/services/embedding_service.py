import time
from functools import lru_cache

from app.config import settings
from app.services.llm_service import LLMError

PROVIDER = settings.embedding_provider
VECTOR_SIZE = 768 if PROVIDER == "gemini" else 384  # local model is 384-d; Gemini is reduced to 768-d
GEMINI_EMBED_MODEL = "gemini-embedding-001"
_RETRY = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL")
_client = None


class EmbeddingError(LLMError):
    pass


@lru_cache(maxsize=1)
def _local_model():
    # Loaded on first use so the API starts fast. Downloads once, then runs locally.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def _gemini_embed(texts: list[str], task: str) -> list[list[float]]:
    global _client
    from google import genai
    from google.genai import types

    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    out: list[list[float]] = []
    for i in range(0, len(texts), 50):
        batch = texts[i : i + 50]
        delay = 2
        for attempt in range(4):
            try:
                result = _client.models.embed_content(
                    model=GEMINI_EMBED_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type=task, output_dimensionality=VECTOR_SIZE),
                )
                out.extend([list(e.values) for e in result.embeddings])
                break
            except Exception as exc:
                if attempt < 3 and any(m in str(exc) for m in _RETRY):
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise EmbeddingError(str(exc)) from exc
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    if PROVIDER == "gemini":
        return _gemini_embed(texts, "RETRIEVAL_DOCUMENT")
    return _local_model().encode(texts, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    if PROVIDER == "gemini":
        return _gemini_embed([text], "RETRIEVAL_QUERY")[0]
    return embed_texts([text])[0]
