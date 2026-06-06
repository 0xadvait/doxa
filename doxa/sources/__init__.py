"""Source loader registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from doxa.schema import DoxaError, SourceRecord


def _metadata_overrides(source: SourceRecord, *, title: str = "", author: str = "", url: str = "") -> SourceRecord:
    if title:
        source.title = title
    if author:
        source.author = author
    if url:
        source.url = url
    return source


def _configured_fetcher(config: dict[str, Any] | None, via: str | None) -> str:
    if via:
        return via
    sources_config = (config or {}).get("sources") or {}
    return str(sources_config.get("fetcher") or "requests")


def load_source(
    location: str,
    *,
    config: dict[str, Any] | None = None,
    via: str | None = None,
    stdin_text: str | None = None,
    title: str = "",
    author: str = "",
    url: str = "",
    fetch_prompt: str | None = None,
) -> SourceRecord:
    """Load a local file or remote URL into a source record."""

    if location == "-":
        from .text import load_stdin_text

        return load_stdin_text(stdin_text or "", title=title, author=author, url=url)

    lowered = location.lower()
    if lowered.startswith(("http://", "https://")):
        if "youtube.com/" in lowered or "youtu.be/" in lowered:
            from .youtube import load_youtube

            return _metadata_overrides(load_youtube(location), title=title, author=author, url=url)
        from .url import load_url

        return _metadata_overrides(
            load_url(location, fetcher=_configured_fetcher(config, via), config=config, fetch_prompt=fetch_prompt),
            title=title,
            author=author,
            url=url,
        )
    path = Path(location).expanduser()
    if not path.exists():
        raise DoxaError(f"Source does not exist: {location}")
    if path.suffix.lower() == ".pdf":
        from .pdf import load_pdf

        return _metadata_overrides(load_pdf(path), title=title, author=author, url=url)
    if path.suffix.lower() in {".txt", ".md", ".text"}:
        from .text import load_text

        return load_text(path, title=title, author=author, url=url)
    raise DoxaError(f"Unsupported source type for {location}. Use .txt, .md, .pdf, URL, or YouTube URL.")
