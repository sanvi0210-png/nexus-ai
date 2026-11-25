from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

app = FastAPI(title="NEXUS AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def warm_up():
    from app.services.embedding_service import embed_query
    from app.services.retrieval_service import rerank

    embed_query("warm up")
    rerank("warm up", [{"text": "warm up"}], 1)
