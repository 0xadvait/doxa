from __future__ import annotations

import pytest

from doxa.schema import DoxaError
from doxa.sources import load_source


def test_stdin_source_uses_metadata() -> None:
    source = load_source(
        "-",
        stdin_text="Trust thyself: every heart vibrates to that iron string.",
        title="Self-Reliance excerpt",
        author="Ralph Waldo Emerson",
        url="https://example.com/emerson",
    )
    assert source.path == "-"
    assert source.title == "Self-Reliance excerpt"
    assert source.author == "Ralph Waldo Emerson"
    assert source.url == "https://example.com/emerson"
    assert "Trust thyself" in source.text


def test_text_source_metadata_can_be_overridden() -> None:
    source = load_source(
        "examples/demo/sources/emerson-self-reliance.txt",
        title="Override title",
        author="Override author",
        url="https://example.com/source",
    )
    assert source.title == "Override title"
    assert source.author == "Override author"
    assert source.url == "https://example.com/source"


def test_brightdata_missing_token_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRIGHTDATA_API_TOKEN", raising=False)
    monkeypatch.delenv("BRIGHTDATA_ZONE", raising=False)
    config = {
        "sources": {
            "fetcher": "brightdata",
            "brightdata": {
                "api_token_env": "BRIGHTDATA_API_TOKEN",
                "zone_env": "BRIGHTDATA_ZONE",
            },
        }
    }
    with pytest.raises(DoxaError, match="set BRIGHTDATA_API_TOKEN"):
        load_source("https://example.com", config=config, via="brightdata")
