from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    workspace_id: str = Field(default="default", min_length=1, max_length=64)
    top_k: int = Field(default=5, ge=1, le=15)
    mode: str | None = None  # semantic | hybrid | hybrid_rerank


class Citation(BaseModel):
    marker: str
    document_id: str
    filename: str
    page: int
    excerpt: str
    score: float = 0.0


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool = False


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    workspace_id: str
    pages: int
    chunks: int


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    workspace_id: str = Field(default="default", min_length=1, max_length=64)


class ResearchResponse(BaseModel):
    report: str
    plan: list[str]
    citations: list[Citation]
    trace: list[str]
    verified: bool
    warnings: list[str] = []
