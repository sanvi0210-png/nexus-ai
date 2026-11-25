from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.config import settings
from app.services.embedding_service import embed_query, embed_texts

client = QdrantClient(path=settings.qdrant_path)
corpus_version = 0  # bumped on every change so the BM25 cache knows to rebuild
VECTOR_SIZE = 384  # all-MiniLM-L6-v2. Recreate the collection if you change the model.


def ensure_collection():
    if not client.collection_exists(settings.collection_name):
        client.create_collection(
            collection_name=settings.collection_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )


def add_chunks(chunks: list[dict], workspace_id: str, document_id: str) -> None:
    global corpus_version
    ensure_collection()
    corpus_version += 1
    vectors = embed_texts([c["text"] for c in chunks])
    points = [
        models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"{document_id}:{i}")),
            vector=vector,
            payload={**chunk, "workspace_id": workspace_id, "document_id": document_id},
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    if points:
        client.upsert(collection_name=settings.collection_name, points=points)


def search_chunks(question: str, workspace_id: str, top_k: int = 5) -> list[dict]:
    ensure_collection()
    result = client.query_points(
        collection_name=settings.collection_name,
        query=embed_query(question),
        query_filter=models.Filter(
            must=[models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return [{"id": str(p.id), "score": p.score, **(p.payload or {})} for p in result.points]


def delete_document_vectors(document_id: str) -> None:
    global corpus_version
    ensure_collection()
    corpus_version += 1
    client.delete(
        collection_name=settings.collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        ),
    )


def all_chunks(workspace_id: str) -> list[dict]:
    """Every chunk of a workspace (used to build the BM25 keyword index)."""
    ensure_collection()
    flt = models.Filter(
        must=[models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))]
    )
    out, offset = [], None
    while True:
        points, offset = client.scroll(
            collection_name=settings.collection_name, scroll_filter=flt,
            limit=256, offset=offset, with_payload=True, with_vectors=False,
        )
        out += [{"id": str(p.id), **(p.payload or {})} for p in points]
        if offset is None:
            return out
