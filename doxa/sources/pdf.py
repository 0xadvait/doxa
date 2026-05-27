"""PDF source loader."""

from __future__ import annotations

from pathlib import Path
import uuid

from doxa.schema import DoxaError, SourceRecord


def load_pdf(path: Path) -> SourceRecord:
    try:
        import fitz
    except ImportError as exc:
        raise DoxaError("PDF ingestion requires the pdf extra: install doxa[pdf].") from exc
    doc = fitz.open(path)
    try:
        text = "\n\n".join(page.get_text("text") for page in doc)
        metadata = doc.metadata or {}
    finally:
        doc.close()
    source_id = "src_" + uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())).hex[:12]
    return SourceRecord(
        id=source_id,
        title=str(metadata.get("title") or path.stem.replace("-", " ").title()),
        author=str(metadata.get("author") or ""),
        date=str(metadata.get("creationDate") or ""),
        url="",
        path=str(path),
        text=text,
    )

