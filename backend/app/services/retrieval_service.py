import re

from rank_bm25 import BM25Okapi

from app.config import settings
from app.services import vector_service as vs
from app.services.fusion import reciprocal_rank_fusion

MODES = ("semantic", "hybrid", "hybrid_rerank")
_bm25_cache: dict[str, tuple[int, BM25Okapi, list[dict]]] = {}
_reranker = None


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _bm25(workspace_id: str):
    cached = _bm25_cache.get(workspace_id)
    if cached and cached[0] == vs.corpus_version:
        return cached[1], cached[2]
    chunks = vs.all_chunks(workspace_id)
    if not chunks:
        return None, []
    index = BM25Okapi([_tokens(c["text"]) for c in chunks])
    _bm25_cache[workspace_id] = (vs.corpus_version, index, chunks)
    return index, chunks


def keyword_hits(question: str, workspace_id: str, n: int) -> list[dict]:
    index, chunks = _bm25(workspace_id)
    if index is None:
        return []
    scores = index.get_scores(_tokens(question))
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:n]
    return [{**chunks[i], "score": 0.0} for i in order if scores[i] > 0]


def rerank(question: str, passages: list[dict], keep: int) -> list[dict]:
    global _reranker
    if not passages:
        return []
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = _reranker.predict([(question, p["text"]) for p in passages])
    ranked = sorted(zip(passages, scores), key=lambda pair: float(pair[1]), reverse=True)
    return [p for p, _ in ranked[:keep]]


def retrieve(question: str, workspace_id: str, top_k: int = 5, mode: str | None = None):
    """Return (hits, best_semantic_score). The best semantic score drives abstention."""
    mode = mode or settings.retrieval_mode
    if mode not in MODES:
        mode = "hybrid"
    n = max(20, top_k * 4)
    semantic = vs.search_chunks(question, workspace_id, n)
    best = semantic[0]["score"] if semantic else 0.0
    if mode == "semantic":
        return semantic[:top_k], best
    fused = reciprocal_rank_fusion([semantic, keyword_hits(question, workspace_id, n)])
    if mode == "hybrid":
        return fused[:top_k], best
    return rerank(question, fused[:n], top_k), best
