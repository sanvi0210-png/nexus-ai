def make_chunks(pages: list[dict], chunk_size: int = 900, overlap: int = 140) -> list[dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks = []
    for item in pages:
        text = item["text"]
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append({"text": piece, "page": item["page"], "filename": item["filename"]})
            if end == len(text):
                break
            start = end - overlap
    return chunks
