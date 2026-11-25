"""Tiny JSON registry of uploaded documents. Replace with SQL in the auth phase (guide section 15)."""
import json
import threading
from pathlib import Path

_PATH = Path("data/documents.json")
_LOCK = threading.Lock()


def _load() -> list[dict]:
    if not _PATH.exists():
        return []
    return json.loads(_PATH.read_text(encoding="utf-8"))


def _save(rows: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def add_document(row: dict) -> None:
    with _LOCK:
        rows = _load()
        rows.append(row)
        _save(rows)


def list_documents(workspace_id: str) -> list[dict]:
    return [r for r in _load() if r["workspace_id"] == workspace_id]


def get_document(document_id: str) -> dict | None:
    return next((r for r in _load() if r["document_id"] == document_id), None)


def remove_document(document_id: str) -> None:
    with _LOCK:
        _save([r for r in _load() if r["document_id"] != document_id])
