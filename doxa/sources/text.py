"""Plain text source loader."""

from __future__ import annotations

import uuid
from pathlib import Path

from doxa.schema import DoxaError, SourceRecord


def _parse_metadata(text: str, path: Path) -> tuple[dict[str, str], str]:
    meta = {"title": path.stem.replace("-", " ").title(), "author": "", "date": "", "url": ""}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), -1)
        if end > 0:
            for line in lines[1:end]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    if key in meta:
                        meta[key] = value.strip()
            text = "\n".join(lines[end + 1 :]).strip()
    return meta, text


def _apply_overrides(meta: dict[str, str], *, title: str = "", author: str = "", url: str = "") -> dict[str, str]:
    if title:
        meta["title"] = title
    if author:
        meta["author"] = author
    if url:
        meta["url"] = url
    return meta


def load_text(path: Path, *, title: str = "", author: str = "", url: str = "") -> SourceRecord:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_metadata(text, path)
    meta = _apply_overrides(meta, title=title, author=author, url=url)
    source_id = "src_" + uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())).hex[:12]
    return SourceRecord(
        id=source_id,
        title=meta["title"],
        author=meta["author"],
        date=meta["date"],
        url=meta["url"],
        path=str(path),
        text=body,
    )


def load_stdin_text(text: str, *, title: str = "", author: str = "", url: str = "") -> SourceRecord:
    body = text.strip()
    if not body:
        raise DoxaError("No stdin text received. Pipe text into `doxa ingest -`.")
    meta = {
        "title": title or "Standard input",
        "author": author,
        "date": "",
        "url": url,
    }
    source_key = "\n".join([meta["title"], meta["author"], meta["url"], body])
    source_id = "src_" + uuid.uuid5(uuid.NAMESPACE_URL, f"stdin:{source_key}").hex[:12]
    return SourceRecord(
        id=source_id,
        title=meta["title"],
        author=meta["author"],
        date=meta["date"],
        url=meta["url"],
        path="-",
        text=body,
    )
