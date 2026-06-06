"""Pluggable URL fetchers.

doxa is not tied to one scraping method. A fetcher is any callable
``(url, config) -> (text, content_type)``; they are looked up by name from a
registry so a user can pick ``requests`` (plain HTTP), a managed reader/scraper
(``jina``, ``firecrawl``, ``brightdata``), or shell out to ANY tool/MCP bridge
via the generic ``command`` fetcher. Third parties can add their own with
``register_fetcher``.

Each fetcher reads its own settings under ``sources.<name>`` in the config and
returns ``(text, content_type)``; ``source_from_url_content`` in url.py turns
that into a SourceRecord (HTML extraction, markdown passthrough, or plain text).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from doxa.schema import DoxaError

FetcherFn = Callable[[str, dict[str, Any]], "tuple[str, str]"]


def _sources_cfg(config: dict[str, Any], name: str) -> dict[str, Any]:
    return ((config.get("sources") or {}).get(name)) or {}


# --- built-in fetchers -------------------------------------------------------

def _requests(url: str, config: dict[str, Any]) -> tuple[str, str]:
    from .url import fetch_url_requests  # lazy to avoid an import cycle

    return fetch_url_requests(url)


def _brightdata(url: str, config: dict[str, Any]) -> tuple[str, str]:
    from .brightdata import fetch_url_brightdata

    return fetch_url_brightdata(url, config)


def _jina(url: str, config: dict[str, Any]) -> tuple[str, str]:
    """Jina AI Reader (https://r.jina.ai) -- clean markdown, free, key optional."""
    cfg = _sources_cfg(config, "jina")
    base = str(cfg.get("base_url") or "https://r.jina.ai").rstrip("/")
    key_env = str(cfg.get("api_key_env") or "JINA_API_KEY")
    headers = {
        "User-Agent": "doxa/0.1",
        "Accept": "text/markdown, text/plain, */*",
        "X-Return-Format": "markdown",
    }
    key = os.environ.get(key_env)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = Request(f"{base}/{url}", headers=headers)
    try:
        with urlopen(request, timeout=90) as response:
            content_type = response.headers.get("content-type", "")
            raw = response.read()
    except HTTPError as exc:
        raise DoxaError(
            f"Jina Reader fetch failed for {url}: HTTP {exc.code}. "
            f"Set {key_env} for higher limits, or use `--via requests`."
        ) from exc
    except OSError as exc:
        raise DoxaError(f"Jina Reader fetch failed for {url}: {exc}") from exc
    return raw.decode("utf-8", errors="replace"), content_type or "text/markdown"


def _firecrawl(url: str, config: dict[str, Any]) -> tuple[str, str]:
    """Firecrawl scrape API -- markdown, requires an API key."""
    cfg = _sources_cfg(config, "firecrawl")
    base = str(cfg.get("base_url") or "https://api.firecrawl.dev").rstrip("/")
    key_env = str(cfg.get("api_key_env") or "FIRECRAWL_API_KEY")
    key = os.environ.get(key_env)
    if not key:
        raise DoxaError(
            f"Firecrawl fetcher is selected; set {key_env} to your Firecrawl API key, "
            "or use `--via jina` (free) or pipe text with `doxa ingest -`."
        )
    path = str(cfg.get("scrape_path") or "/v2/scrape")
    payload = json.dumps({"url": url, "formats": ["markdown"]}).encode("utf-8")
    request = Request(
        f"{base}{path}",
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "doxa/0.1"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()[:500]
        raise DoxaError(f"Firecrawl fetch failed for {url}: HTTP {exc.code}: {detail}") from exc
    except OSError as exc:
        raise DoxaError(f"Firecrawl fetch failed for {url}: {exc}") from exc
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise DoxaError(f"Firecrawl returned non-JSON for {url}.") from exc
    body = data.get("data") or {}
    markdown = body.get("markdown") or body.get("content") or ""
    if not markdown:
        raise DoxaError(f"Firecrawl returned no markdown for {url}.")
    return markdown, "text/markdown"


def _command(url: str, config: dict[str, Any]) -> tuple[str, str]:
    """Run a user-configured command that fetches the URL and prints text to stdout.

    The universal escape hatch: wire ANY scraper or MCP bridge. Configure either
    ``sources.command.argv`` (a list, recommended -- no shell) or
    ``sources.command.shell`` (a string run via the shell); ``{url}`` is replaced
    with the target URL in each.
    """
    cfg = _sources_cfg(config, "command")
    argv = cfg.get("argv")
    shell = cfg.get("shell")
    timeout = int(cfg.get("timeout", 120))
    if argv:
        cmd: Any = [str(part).replace("{url}", url) for part in argv]
        use_shell = False
    elif shell:
        cmd = str(shell).replace("{url}", url)
        use_shell = True
    else:
        raise DoxaError(
            "command fetcher is selected; set sources.command.argv (a list) or "
            "sources.command.shell (a string) with a {url} placeholder."
        )
    try:
        proc = subprocess.run(cmd, shell=use_shell, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise DoxaError(f"command fetcher: executable not found ({exc}).") from exc
    except subprocess.TimeoutExpired:
        raise DoxaError(f"command fetcher timed out after {timeout}s for {url}.") from None
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()[:500]
        raise DoxaError(f"command fetcher failed (exit {proc.returncode}) for {url}: {detail}")
    if not proc.stdout.strip():
        raise DoxaError(f"command fetcher returned no output for {url}.")
    return proc.stdout, str(cfg.get("content_type") or "text/markdown")


# --- agent fetchers: delegate the fetch to a coding agent's browsing ----------
# A coding agent (Claude Code, Codex, Hermes) can fetch JS-heavy or bot-walled
# pages with its own browser/web tools and return clean markdown. These presets
# are thin wrappers over the same subprocess machinery as `command`, with the
# right per-CLI invocation; everything (argv, prompt, timeout) is overridable
# under sources.<name>.

_SCRAPE_PROMPT = (
    "Fetch the web page at {url} and output ONLY its main readable content as clean "
    "Markdown. No commentary, no preamble, no code fences, no tool logs -- just the content."
)

_AGENT_PRESETS: dict[str, dict[str, Any]] = {
    # claude -p prints the response text to stdout
    "claude": {"argv": ["claude", "-p", "{prompt}"], "capture": "stdout"},
    # codex exec -o writes only the final message to a file (clean output)
    "codex": {
        "argv": ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
                 "--skip-git-repo-check", "-o", "{outfile}", "{prompt}"],
        "capture": "outfile",
    },
    # hermes -z runs a one-shot prompt; --yolo skips approvals for unattended use
    "hermes": {"argv": ["hermes", "--yolo", "-z", "{prompt}"], "capture": "stdout"},
}


def _agent_fetch(name: str) -> FetcherFn:
    def fetch(url: str, config: dict[str, Any]) -> tuple[str, str]:
        import shutil
        import tempfile

        preset = _AGENT_PRESETS[name]
        cfg = _sources_cfg(config, name)
        prompt = str(cfg.get("prompt") or _SCRAPE_PROMPT).replace("{url}", url)
        argv_template = cfg.get("argv") or preset["argv"]
        capture = str(cfg.get("capture") or preset["capture"])
        timeout = int(cfg.get("timeout", 300))

        outfile = ""
        if capture == "outfile" or any("{outfile}" in str(part) for part in argv_template):
            handle, outfile = tempfile.mkstemp(prefix="doxa_agent_", suffix=".md")
            os.close(handle)
        try:
            argv = [
                str(part).replace("{prompt}", prompt).replace("{url}", url).replace("{outfile}", outfile)
                for part in argv_template
            ]
            if shutil.which(argv[0]) is None:
                raise DoxaError(
                    f"'{name}' fetcher needs the '{argv[0]}' CLI on PATH. Install it, "
                    f"set sources.{name}.argv, or use `--via jina` / `--via requests`."
                )
            try:
                proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise DoxaError(f"'{name}' fetcher timed out after {timeout}s for {url}.") from None
            if proc.returncode != 0:
                detail = (proc.stderr or "").strip()[:500]
                raise DoxaError(f"'{name}' fetcher failed (exit {proc.returncode}) for {url}: {detail}")
            if capture == "outfile":
                text = ""
                if outfile and os.path.exists(outfile):
                    with open(outfile, encoding="utf-8") as handle:
                        text = handle.read()
            else:
                text = proc.stdout
        finally:
            if outfile and os.path.exists(outfile):
                os.unlink(outfile)
        if not text.strip():
            raise DoxaError(f"'{name}' fetcher returned no output for {url}.")
        return text, str(cfg.get("content_type") or "text/markdown")

    return fetch


_FETCHERS: dict[str, FetcherFn] = {
    "requests": _requests,
    "brightdata": _brightdata,
    "jina": _jina,
    "firecrawl": _firecrawl,
    "command": _command,
    "claude": _agent_fetch("claude"),
    "codex": _agent_fetch("codex"),
    "hermes": _agent_fetch("hermes"),
}


def register_fetcher(name: str, fetcher: FetcherFn) -> None:
    """Register a custom fetcher: ``(url, config) -> (text, content_type)``."""
    _FETCHERS[name] = fetcher


def available_fetchers() -> list[str]:
    return list(_FETCHERS)


def get_fetcher(name: str) -> FetcherFn:
    fetcher = _FETCHERS.get(name)
    if fetcher is None:
        raise DoxaError(f"Unknown URL fetcher '{name}'. Available: {', '.join(_FETCHERS)}.")
    return fetcher
