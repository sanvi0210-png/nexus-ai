from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

app = FastAPI(title="NEXUS AI API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.on_event("startup")
def warm_up():
    # Local models: load them at startup so the first visitor does not wait.
    if settings.embedding_provider != "local":
        return
    from app.services.embedding_service import embed_query
    from app.services.retrieval_service import rerank, rerank_available

    embed_query("warm up")
    if rerank_available():
        rerank("warm up", [{"text": "warm up"}], 1)


@app.get("/health")
def health():
    return {"status": "ok"}
