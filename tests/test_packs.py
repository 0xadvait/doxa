"""Starter packs: registry loads, export normalizes + strips source text, install roundtrips."""
from __future__ import annotations

import json

import pytest

from doxa.cli import main
from doxa.config import load_config
from doxa.packs import export_pack, get_pack, install_pack, load_registry
from doxa.schema import DoxaError
from doxa.store import JsonlStore


def test_registry_has_startup_wisdom() -> None:
    names = {p["name"] for p in load_registry()}
    assert "startup-wisdom" in names
    pack = get_pack("startup-wisdom")
    assert pack.get("sources") and pack.get("license") and pack.get("url")


def test_get_pack_unknown_raises() -> None:
    with pytest.raises(DoxaError):
        get_pack("does-not-exist")


def test_export_normalizes_filters_and_strips_text(tmp_path) -> None:
    beliefs = tmp_path / "b.jsonl"
    quotes = tmp_path / "q.jsonl"
    beliefs.write_text(
        "\n".join([
            # private-shaped: string conviction + ingest + extra fields
            json.dumps({"id": "b1", "belief": "X", "reasoning": "r", "stance": "endorses",
                        "conviction": "strong", "angle": "drop me", "ingest": "keep", "tags": ["t"],
                        "source": {"title": "S", "author": "A", "url": "u"}}),
            json.dumps({"id": "b2", "belief": "Y", "reasoning": "r", "stance": "supports",
                        "conviction": 0.5, "ingest": "other", "source": {"title": "S2"}}),
        ]),
        encoding="utf-8",
    )
    quotes.write_text(
        json.dumps({"id": "q1", "quote": "hello world", "speaker": "A", "context": "c",
                    "belief_ids": ["b1"], "source": {"title": "S", "url": "u"}}),
        encoding="utf-8",
    )
    out = tmp_path / "pack"
    counts = export_pack(beliefs_path=beliefs, quotes_path=quotes, ingests=["keep"], out_dir=out, meta={"name": "p"})
    assert counts == {"beliefs": 1, "quotes": 1, "sources": 1}

    belief = json.loads((out / "beliefs.jsonl").read_text().splitlines()[0])
    assert belief["id"] == "b1"
    assert isinstance(belief["conviction"], float) and belief["conviction"] > 0.5  # "strong" -> 0.85
    assert "ingest" not in belief and "angle" not in belief  # private-only fields dropped
    # citation index: source records carry NO full text
    assert json.loads((out / "sources.jsonl").read_text().splitlines()[0])["text"] == ""


def test_install_auto_creates_base_and_dedups(tmp_path, monkeypatch) -> None:
    beliefs = tmp_path / "b.jsonl"
    beliefs.write_text(
        json.dumps({"id": "b1", "belief": "X", "reasoning": "r", "stance": "supports",
                    "conviction": 0.8, "source": {"title": "S", "url": "u"}}),
        encoding="utf-8",
    )
    out = tmp_path / "pack"
    export_pack(beliefs_path=beliefs, quotes_path=None, ingests=None, out_dir=out, meta={"name": "p"})

    monkeypatch.chdir(tmp_path)
    assert main(["packs", "install", str(out)]) == 0          # no base -> auto-creates one
    assert (tmp_path / "doxa.yaml").exists()

    store = JsonlStore(load_config(tmp_path / "doxa.yaml", allow_demo_default=False))
    assert len(store.beliefs()) == 1
    again = install_pack(str(out), store)                      # idempotent
    assert again["beliefs"] == 0 and again["skipped"] == 1
