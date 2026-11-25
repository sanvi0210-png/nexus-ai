import pytest
from fastapi.testclient import TestClient

from tests.helpers import fake_embed, make_pdf


@pytest.fixture()
def client(monkeypatch):
    from app.services import rag_service, vector_service

    monkeypatch.setattr(vector_service, "embed_texts", lambda texts: [fake_embed(t) for t in texts])
    monkeypatch.setattr(vector_service, "embed_query", fake_embed)
    monkeypatch.setattr(rag_service, "generate", lambda prompt: "Reranking raises precision [S1]. Fake [S9].")
    from app.main import app

    return TestClient(app)


def _upload(client, name, pages, ws="t1"):
    return client.post(f"/api/documents/upload?workspace_id={ws}",
                       files={"file": (name, make_pdf(pages), "application/pdf")})


def test_upload_ask_delete_flow(client):
    r = _upload(client, "paper-b.pdf", ["Reranking improves precision of retrieval results", "Agents plan multi step research"])
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["pages"] == 2 and doc["chunks"] >= 2

    assert [d["filename"] for d in client.get("/api/documents?workspace_id=t1").json()] == ["paper-b.pdf"]

    for mode in ("semantic", "hybrid"):
        a = client.post("/api/ask", json={"question": "How does reranking improve precision?", "workspace_id": "t1", "mode": mode})
        assert a.status_code == 200, a.text
        body = a.json()
        assert not body["insufficient_evidence"]
        assert "[S9]" not in body["answer"]  # invented marker removed
        assert body["citations"][0]["filename"] == "paper-b.pdf"

    # unrelated question and other workspace both abstain
    off = client.post("/api/ask", json={"question": "zebra giraffe savannah", "workspace_id": "t1"}).json()
    assert off["insufficient_evidence"]
    other = client.post("/api/ask", json={"question": "reranking precision", "workspace_id": "other"}).json()
    assert other["insufficient_evidence"]

    assert client.delete(f"/api/documents/{doc['document_id']}").status_code == 200
    assert client.get("/api/documents?workspace_id=t1").json() == []
    gone = client.post("/api/ask", json={"question": "reranking precision", "workspace_id": "t1"}).json()
    assert gone["insufficient_evidence"]


def test_rejects_fake_pdf(client):
    r = client.post("/api/documents/upload", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400
