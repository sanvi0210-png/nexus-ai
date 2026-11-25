import pytest

from app.services.chunk_service import make_chunks


def test_chunking_preserves_page_metadata():
    pages = [{"page": 3, "filename": "sample.pdf", "text": "A" * 2000}]
    chunks = make_chunks(pages, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(c["page"] == 3 and c["filename"] == "sample.pdf" for c in chunks)


def test_chunking_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        make_chunks([], chunk_size=100, overlap=100)


def test_short_page_gives_one_chunk():
    chunks = make_chunks([{"page": 1, "filename": "a.pdf", "text": "short text"}])
    assert len(chunks) == 1
