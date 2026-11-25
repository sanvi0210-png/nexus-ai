from app.services import agent_service


def _stub(monkeypatch, verifier_replies):
    ev = [{"id": "1", "filename": "a.pdf", "page": 2, "text": "Reranking helps.", "document_id": "d", "score": 0.9}]
    monkeypatch.setattr(agent_service, "retrieve", lambda q, ws, top_k=4, mode=None: (ev, 0.9))
    calls = {"n": 0, "verifier": iter(verifier_replies)}

    def fake_generate(prompt):
        calls["n"] += 1
        if "Break this research question" in prompt:
            return '["what is reranking", "why use it"]'
        if "strict fact-checker" in prompt:
            return next(calls["verifier"])
        return "## Key findings\nReranking helps [S1]."

    monkeypatch.setattr(agent_service, "generate", fake_generate)
    agent_service._app = None


def test_agent_happy_path(monkeypatch):
    _stub(monkeypatch, ['{"unsupported": []}'])
    out = agent_service.run_research("Why rerank?", "w")
    assert out["verified"] and out["plan"] == ["what is reranking", "why use it"]
    assert out["citations"][0]["filename"] == "a.pdf" and "Sources" in out["report"]


def test_agent_revises_once_then_flags(monkeypatch):
    _stub(monkeypatch, ['{"unsupported": ["bad claim"]}', '{"unsupported": ["bad claim"]}'])
    out = agent_service.run_research("Why rerank?", "w")
    assert not out["verified"] and "Unverified claims" in out["report"]
    assert sum("Analyst" in t for t in out["trace"]) == 2  # exactly one revision, no endless loop


def test_agent_stops_without_evidence(monkeypatch):
    _stub(monkeypatch, [])
    monkeypatch.setattr(agent_service, "retrieve", lambda *a, **k: ([], 0.0))
    out = agent_service.run_research("Anything?", "w")
    assert not out["verified"] and "No sufficiently relevant evidence" in out["report"]
