from pathlib import Path

from pypdf import PdfReader


def extract_pdf_pages(file_path: str) -> list[dict]:
    """Extract text page by page so every chunk keeps its page number."""
    path = Path(file_path)
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = " ".join(text.split())
        if text:
            pages.append({"page": page_number, "text": text, "filename": path.name})
    return pages
