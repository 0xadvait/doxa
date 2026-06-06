from __future__ import annotations

import subprocess
from copy import deepcopy

import pytest

from doxa.cli import main
from doxa.config import DEFAULT_CONFIG, load_config
from doxa.providers.codex_cli import CodexCliProvider
from doxa.schema import Belief, DoxaError, Quote, SourceRecord, SourceRef
from doxa.sources.fetchers import get_fetcher
from doxa.sources.url import load_url
from doxa.store import JsonlStore, postgres_table_prefix


def _config(tmp_path):
    (tmp_path / "doxa.yaml").write_text("project:\n  name: t\n", encoding="utf-8")
    return load_config(tmp_path / "doxa.yaml", allow_demo_default=False)


def test_remove_source_uses_source_id_not_title_url_collision(tmp_path) -> None:
    config = _config(tmp_path)
    store = JsonlStore(config)
    source_a = SourceRecord(id="src_a", title="Same", author="", date="", url="", path="a.txt", text="A")
    source_b = SourceRecord(id="src_b", title="Same", author="", date="", url="", path="b.txt", text="B")
    ref_a = SourceRef(id="src_a", title="Same", url="")
    ref_b = SourceRef(id="src_b", title="Same", url="")
    belief_a = Belief(id="b_a", belief="A", reasoning="r", stance="supports", conviction=0.8, source=ref_a)
    belief_b = Belief(id="b_b", belief="B", reasoning="r", stance="supports", conviction=0.8, source=ref_b)
    quote_a = Quote(id="q_a", quote="A", speaker="", source=ref_a, context="", belief_ids=["b_a"])
    quote_b = Quote(id="q_b", quote="B", speaker="", source=ref_b, context="", belief_ids=["b_b"])
    store.write_all([belief_a, belief_b], [quote_a, quote_b], [source_a, source_b])

    removed = store.remove_source("src_a")

    assert removed == {"beliefs": 1, "quotes": 1, "sources": 1}
    assert [source.id for source in store.sources()] == ["src_b"]
    assert [belief.id for belief in store.beliefs()] == ["b_b"]
    assert [quote.id for quote in store.quotes()] == ["q_b"]


def test_sources_list_counts_by_source_id(tmp_path, capsys) -> None:
    config = _config(tmp_path)
    store = JsonlStore(config)
    source_a = SourceRecord(id="src_a", title="Same", author="", date="", url="", path="a.txt", text="A")
    source_b = SourceRecord(id="src_b", title="Same", author="", date="", url="", path="b.txt", text="B")
    ref_a = source_a.ref
    ref_b = source_b.ref
    store.write_all(
        [
            Belief(id="b_a", belief="A", reasoning="r", stance="supports", conviction=0.8, source=ref_a),
            Belief(id="b_b", belief="B", reasoning="r", stance="supports", conviction=0.8, source=ref_b),
        ],
        [
            Quote(id="q_a", quote="A", speaker="", source=ref_a, context="", belief_ids=["b_a"]),
            Quote(id="q_b", quote="B", speaker="", source=ref_b, context="", belief_ids=["b_b"]),
        ],
        [source_a, source_b],
    )

    assert main(["sources", "list", "--config", str(tmp_path / "doxa.yaml")]) == 0
    out = capsys.readouterr().out

    assert "src_a  Same  [beliefs 1, quotes 1]" in out
    assert "src_b  Same  [beliefs 1, quotes 1]" in out


def test_postgres_table_prefix_rejects_invalid_identifier() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["postgres"]["table_prefix"] = "doxa; drop table doxa_beliefs"

    with pytest.raises(DoxaError, match="table_prefix"):
        postgres_table_prefix(config)


def test_url_ingestion_rejects_non_http_schemes() -> None:
    with pytest.raises(DoxaError, match="Only http"):
        load_url("file:///etc/passwd", fetcher="requests", config={})


def test_command_shell_requires_explicit_opt_in() -> None:
    config = {"sources": {"command": {"shell": "printf '# X\\n\\nbody'"}}}

    with pytest.raises(DoxaError, match="allow_shell"):
        get_fetcher("command")("https://example.com", config)


def test_command_shell_runs_only_when_explicitly_allowed() -> None:
    config = {"sources": {"command": {"shell": "printf '# X\\n\\nbody'", "allow_shell": True}}}

    text, content_type = get_fetcher("command")("https://example.com", config)

    assert "# X" in text
    assert content_type == "text/markdown"


def test_default_config_does_not_ship_dangerous_codex_flag() -> None:
    flags = DEFAULT_CONFIG["providers"]["codex-cli"]["flags"]

    assert not any("dangerously" in flag for flag in flags)
    assert DEFAULT_CONFIG["providers"]["codex-cli"]["timeout"] > 0
    assert DEFAULT_CONFIG["providers"]["claude-cli"]["timeout"] > 0


def test_codex_provider_timeout_is_reported(monkeypatch) -> None:
    monkeypatch.setattr("doxa.providers.codex_cli.shutil.which", lambda binary: f"/bin/{binary}")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=7)

    monkeypatch.setattr("doxa.providers.codex_cli.subprocess.run", fake_run)
    provider = CodexCliProvider({"providers": {"codex-cli": {"binary": "codex", "timeout": 7}}})

    with pytest.raises(DoxaError, match="timed out after 7s"):
        provider.complete("system", "user")


def test_semantic_search_skips_stale_postgres_payloads(tmp_path, monkeypatch) -> None:
    from doxa import retrieve

    config = _config(tmp_path)
    store = JsonlStore(config)
    source = SourceRecord(id="src", title="T", author="", date="", url="", path="", text="live")
    ref = source.ref
    store.write_all(
        [Belief(id="b_live", belief="Live", reasoning="r", stance="supports", conviction=0.8, source=ref)],
        [Quote(id="q_live", quote="live", speaker="", source=ref, context="", belief_ids=["b_live"])],
        [source],
    )

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return [({"id": "b_stale", "belief": "Stale"}, 0.99), ({"id": "b_live"}, 0.5)]

    class Conn:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(retrieve, "embed_query", lambda query, cfg: [0.1, 0.2])
    monkeypatch.setattr(retrieve, "postgres_connect", lambda cfg: Conn())

    results = retrieve.semantic_search("live", config, limit=5)

    assert [result.belief.id for result in results] == ["b_live"]


def test_init_writes_compact_config_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["init", "--yes", "--provider", "openai", "--api-key-env", "OPENAI_API_KEY"]) == 0
    config_text = (tmp_path / "doxa.yaml").read_text(encoding="utf-8")

    assert "preferences:" not in config_text
    assert "postgres:" not in config_text
    assert len(config_text.splitlines()) < 60


def test_doctor_passes_for_api_provider_when_env_set(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert main(["init", "--yes", "--provider", "openai", "--api-key-env", "OPENAI_API_KEY"]) == 0
    capsys.readouterr()

    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "Doctor found no blocking issues" in out
