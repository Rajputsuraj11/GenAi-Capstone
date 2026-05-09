import fitz
import chardet
from typing import List, Dict, Any


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from each page of a PDF with metadata.
    Returns list of page dicts with text, page number, encoding info.
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        raw_bytes = text.encode("utf-8", errors="replace")
        detected = chardet.detect(raw_bytes)

        pages.append({
            "page_number": page_num + 1,
            "text": text,
            "char_count": len(text),
            "detected_encoding": detected.get("encoding", "unknown"),
            "encoding_confidence": detected.get("confidence", 0.0),
            "is_empty": len(text.strip()) == 0,
        })

    doc.close()
    return pages


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract PDF metadata (author, title, creation date)."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    page_count = len(doc)
    doc.close()
    return {
        "title": meta.get("title", "Unknown"),
        "author": meta.get("author", "Unknown"),
        "page_count": page_count,
        "format": meta.get("format", "PDF"),
        "creator": meta.get("creator", "Unknown"),
    }
