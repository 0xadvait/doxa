"""URL source loader with standard-library HTML text extraction."""

from __future__ import annotations

import re
import uuid
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from doxa.schema import DoxaError, SourceRecord, normalize_ws


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "li", "h1", "h2", "h3", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.title += data
        self.parts.append(data)


def validate_http_url(url: str) -> str:
    """Return url when it is an http(s) URL, otherwise raise a friendly error."""

    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise DoxaError(f"Only http(s) URLs are supported for URL ingestion: {url}")
    return url


def fetch_url_requests(url: str) -> tuple[str, str]:
    url = validate_http_url(url)
    request = Request(url, headers={"User-Agent": "doxa/0.1"})
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310 - validate_http_url restricts schemes.
            content_type = response.headers.get("content-type", "")
            raw = response.read()
    except OSError as exc:
        raise DoxaError(f"Could not fetch URL {url}: {exc}") from exc
    charset = "utf-8"
    match = re.search(r"charset=([^;\s]+)", content_type)
    if match:
        charset = match.group(1)
    return raw.decode(charset, errors="replace"), content_type


def source_from_url_content(url: str, text: str, content_type: str = "") -> SourceRecord:
    if "html" in content_type.lower() or "<html" in text[:500].lower():
        parser = _TextExtractor()
        parser.feed(text)
        title = normalize_ws(parser.title) or url
        body = normalize_ws("\n".join(parser.parts))
    elif text.lstrip().startswith("#"):
        title = next(
            (line.strip().lstrip("#").strip() for line in text.splitlines() if line.strip().startswith("#")),
            url,
        )
        body = text
    else:
        title = url
        body = text
    source_id = "src_" + uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:12]
    return SourceRecord(id=source_id, title=title, author="", date="", url=url, path=url, text=body)


def load_url(
    url: str,
    *,
    fetcher: str = "requests",
    config: dict[str, Any] | None = None,
    fetch_prompt: str | None = None,
) -> SourceRecord:
    from .fetchers import get_fetcher

    url = validate_http_url(url)
    effective = dict(config or {})
    if fetch_prompt:
        effective["_fetch_prompt"] = fetch_prompt
    text, content_type = get_fetcher(fetcher)(url, effective)
    return source_from_url_content(url, text, content_type)
