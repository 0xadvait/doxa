from __future__ import annotations

import json

import pytest

from doxa.schema import DoxaError
from doxa.sources import fetchers
from doxa.sources.fetchers import available_fetchers, get_fetcher, register_fetcher
from doxa.sources.url import load_url


class _Resp:
    def __init__(self, data: bytes, content_type: str = "text/markdown") -> None:
        self._data = data
        self.headers = {"content-type": content_type}

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc) -> bool:
        return False


def test_registry_lists_builtin_fetchers() -> None:
    names = available_fetchers()
    for name in ("requests", "brightdata", "jina", "firecrawl", "command"):
        assert name in names


def test_unknown_fetcher_is_friendly() -> None:
    with pytest.raises(DoxaError) as exc:
        get_fetcher("nope")
    assert "Unknown URL fetcher" in str(exc.value)
    assert "Available:" in str(exc.value)


def test_register_custom_fetcher_is_usable() -> None:
    register_fetcher("memtest", lambda url, config: ("# Mem\n\nbody " + url, "text/markdown"))
    assert "memtest" in available_fetchers()
    rec = load_url("https://example.com/z", fetcher="memtest", config={})
    assert rec.title == "Mem"
    assert "body https://example.com/z" in rec.text


def test_jina_builds_reader_url_and_returns_markdown(monkeypatch) -> None:
    seen: dict = {}

    def fake_urlopen(request, timeout=0):
        seen["url"] = request.full_url
        return _Resp(b"# Title\n\ncontent", "text/markdown")

    monkeypatch.setattr(fetchers, "urlopen", fake_urlopen)
    text, content_type = get_fetcher("jina")("https://example.com/a", {})
    assert seen["url"] == "https://r.jina.ai/https://example.com/a"
    assert "# Title" in text


def test_firecrawl_requires_key_then_returns_markdown(monkeypatch) -> None:
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    with pytest.raises(DoxaError) as exc:
        get_fetcher("firecrawl")("https://example.com", {})
    assert "FIRECRAWL_API_KEY" in str(exc.value)

    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(
        fetchers,
        "urlopen",
        lambda request, timeout=0: _Resp(json.dumps({"data": {"markdown": "# scraped"}}).encode(), "application/json"),
    )
    text, content_type = get_fetcher("firecrawl")("https://example.com", {})
    assert text == "# scraped"
    assert content_type == "text/markdown"


def test_command_fetcher_runs_argv_with_url(tmp_path) -> None:
    config = {"sources": {"command": {"argv": ["python3", "-c", "import sys;print('# C\\n\\nbody '+sys.argv[1])", "{url}"]}}}
    rec = load_url("https://example.com/x", fetcher="command", config=config)
    assert rec.title == "C"
    assert "body https://example.com/x" in rec.text


def test_command_fetcher_without_argv_is_friendly() -> None:
    with pytest.raises(DoxaError) as exc:
        get_fetcher("command")("https://x", {"sources": {"command": {}}})
    assert "sources.command.argv" in str(exc.value)


def test_command_fetcher_reports_nonzero_exit() -> None:
    config = {"sources": {"command": {"argv": ["python3", "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"]}}}
    with pytest.raises(DoxaError) as exc:
        get_fetcher("command")("https://x", config)
    assert "exit 3" in str(exc.value)


def test_registry_includes_agent_fetchers() -> None:
    for name in ("claude", "codex", "hermes"):
        assert name in available_fetchers()


def test_agent_fetcher_stdout_capture(tmp_path) -> None:
    # claude preset captures stdout; override argv with a fake agent that prints markdown
    config = {"sources": {"claude": {"argv": ["python3", "-c", "import sys;print('# Agent\\n\\nfetched '+sys.argv[1])", "{url}"]}}}
    rec = load_url("https://example.com/p", fetcher="claude", config=config)
    assert rec.title == "Agent"
    assert "fetched https://example.com/p" in rec.text


def test_agent_fetcher_outfile_capture(tmp_path) -> None:
    # codex preset captures from {outfile}; fake agent writes markdown there
    config = {"sources": {"codex": {"argv": ["python3", "-c", "import sys;open(sys.argv[1],'w').write('# Codex\\n\\nfrom file')", "{outfile}"]}}}
    rec = load_url("https://example.com/q", fetcher="codex", config=config)
    assert rec.title == "Codex"
    assert "from file" in rec.text


def test_agent_fetcher_missing_binary_is_friendly() -> None:
    config = {"sources": {"hermes": {"argv": ["doxa_missing_agent_zzz", "{url}"]}}}
    with pytest.raises(DoxaError) as exc:
        get_fetcher("hermes")("https://x", config)
    assert "on PATH" in str(exc.value)


def test_build_fetch_prompt_modes() -> None:
    from doxa.sources.fetchers import build_fetch_prompt

    assert build_fetch_prompt("markdown", None) is None      # default
    assert build_fetch_prompt(None, None) is None
    assert "browser" in (build_fetch_prompt("browser", None) or "").lower()
    assert build_fetch_prompt(None, "just this") == "just this"
    extract = build_fetch_prompt("extract", "name, price")
    assert "JSON" in extract and "name, price" in extract
    with pytest.raises(DoxaError):
        build_fetch_prompt("extract", None)


def test_fetch_prompt_overrides_agent_prompt_and_injects_url() -> None:
    # fake claude echoes the prompt it was handed
    config = {"sources": {"claude": {"argv": ["python3", "-c", "import sys;print('# Got\\n\\n'+sys.argv[1])", "{prompt}"]}}}
    rec = load_url("https://ex.com/p", fetcher="claude", config=config, fetch_prompt="EXTRACT fields as JSON")
    assert "EXTRACT fields as JSON" in rec.text
    assert "https://ex.com/p" in rec.text  # url injected even though the prompt omitted it


def test_command_fetcher_substitutes_prompt() -> None:
    config = {"sources": {"command": {"argv": ["python3", "-c", "import sys;print('# Cmd\\n\\n'+sys.argv[1])", "{prompt}"]}}}
    rec = load_url("https://x", fetcher="command", config=config, fetch_prompt="do the thing")
    assert "do the thing" in rec.text
