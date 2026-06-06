"""BrightData Web Unlocker fetcher."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from doxa.schema import DoxaError

from .url import validate_http_url


BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"


def _config_value(config: dict[str, Any], key: str, default: str) -> str:
    sources_config = config.get("sources") or {}
    brightdata_config = sources_config.get("brightdata") or {}
    return str(brightdata_config.get(key) or default)


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("markdown", "text", "body", "content", "html", "data"):
            extracted = _extract_text(value.get(key))
            if extracted:
                return extracted
        return ""
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := _extract_text(item)))
    return ""


def _decode_error(exc: HTTPError) -> str:
    body = exc.read().decode("utf-8", errors="replace").strip()
    if len(body) > 500:
        body = body[:500] + "..."
    return body


def fetch_url_brightdata(url: str, config: dict[str, Any]) -> tuple[str, str]:
    """Fetch a URL through BrightData Web Unlocker and return page text."""

    url = validate_http_url(url)
    token_env = _config_value(config, "api_token_env", "BRIGHTDATA_API_TOKEN")
    zone_env = _config_value(config, "zone_env", "BRIGHTDATA_ZONE")
    token = os.environ.get(token_env)
    zone = os.environ.get(zone_env)
    if not token:
        raise DoxaError(
            f"BrightData fetcher is selected; set {token_env} to your BrightData API token, "
            "or pipe pre-fetched text with `doxa ingest -`."
        )
    if not zone:
        raise DoxaError(
            f"BrightData fetcher is selected; set {zone_env} to your BrightData Web Unlocker zone, "
            "or pipe pre-fetched text with `doxa ingest -`."
        )

    payload = json.dumps(
        {
            "zone": zone,
            "url": url,
            "format": "raw",
            "data_format": "markdown",
        }
    ).encode("utf-8")
    request = Request(
        BRIGHTDATA_ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/markdown, text/plain, text/html, application/json",
            "User-Agent": "doxa/0.1",
        },
    )
    try:
        with urlopen(request, timeout=90) as response:  # nosec B310 - fixed BrightData endpoint; target URL validated.
            content_type = response.headers.get("content-type", "")
            raw = response.read()
    except HTTPError as exc:
        detail = _decode_error(exc)
        suffix = f": {detail}" if detail else ""
        raise DoxaError(f"BrightData fetch failed for {url}: HTTP {exc.code}{suffix}") from exc
    except OSError as exc:
        raise DoxaError(f"BrightData fetch failed for {url}: {exc}") from exc

    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text, content_type
        extracted = _extract_text(parsed)
        if extracted:
            return extracted, "text/markdown"
    return text, content_type or "text/plain"
