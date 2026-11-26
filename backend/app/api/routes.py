import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.config import settings
from app.schemas import AskRequest, AskResponse, DocumentInfo, ResearchRequest, ResearchResponse
from app.services import registry_service as registry
from app.services.chunk_service import make_chunks
from app.services.limits import rate_limit
from app.services.pdf_service import extract_pdf_pages
from app.services.rag_service import LLMError, answer_question
from app.services.vector_service import add_chunks, delete_document_vectors

router = APIRouter()
WS = r"^[A-Za-z0-9_-]+$"
UPLOAD_DIR = os.path.join(settings.data_dir, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/documents/upload", response_model=DocumentInfo, dependencies=[Depends(rate_limit("upload", 6, cost=2))])
async def upload_document(file: UploadFile = File(...), workspace_id: str = Query("default", max_length=64, pattern=WS)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")

    if len(registry.list_documents(workspace_id)) >= settings.max_docs_per_workspace:
        raise HTTPException(400, f"Demo limit: up to {settings.max_docs_per_workspace} documents per workspace. Delete one first.")

    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "This file is not a valid PDF.")

    document_id = str(uuid4())
    safe_name = os.path.basename(file.filename)
    path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")
    with open(path, "wb") as out:
        out.write(data)

    try:
        pages = extract_pdf_pages(path)
    except Exception:
        os.remove(path)
        raise HTTPException(422, "Could not read this PDF. It may be corrupted or encrypted.")
    if not pages:
        os.remove(path)
        raise HTTPException(422, "No selectable text found. This may be a scanned PDF.")

    if len(pages) > settings.max_pages:
        os.remove(path)
        raise HTTPException(413, f"This PDF has {len(pages)} pages. The limit is {settings.max_pages}.")

    for p in pages:
        p["filename"] = safe_name
    chunks = make_chunks(pages)
    try:
        add_chunks(chunks, workspace_id, document_id)
    except LLMError as exc:
        os.remove(path)
        raise HTTPException(502, f"Could not index this document right now: {exc}")

    row = {
        "document_id": document_id,
        "filename": safe_name,
        "workspace_id": workspace_id,
        "pages": len(pages),
        "chunks": len(chunks),
    }
    registry.add_document(row)
    return row


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents(workspace_id: str = Query("default", max_length=64, pattern=WS)):
    return registry.list_documents(workspace_id)


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    if not registry.get_document(document_id):
        raise HTTPException(404, "Document not found.")
    delete_document_vectors(document_id)
    path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")
    if os.path.exists(path):
        os.remove(path)
    registry.remove_document(document_id)
    return {"deleted": document_id}


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(rate_limit("ask", 15, cost=1))])
def ask(request: AskRequest):
    try:
        return answer_question(request.question, request.workspace_id, request.top_k, request.mode)
    except LLMError as exc:
        raise HTTPException(502, f"The language model request failed: {exc}")


@router.post("/research", response_model=ResearchResponse, dependencies=[Depends(rate_limit("research", 4, cost=5))])
def research(request: ResearchRequest):
    from app.services.agent_service import run_research  # imported lazily: needs `pip install langgraph`

    try:
        return run_research(request.question, request.workspace_id)
    except LLMError as exc:
        raise HTTPException(502, f"The language model request failed: {exc}")


@router.get("/config")
def get_config():
    from app.services.retrieval_service import rerank_available

    return {"rerank": rerank_available(), "embedding_provider": settings.embedding_provider}
