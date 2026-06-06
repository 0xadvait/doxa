from __future__ import annotations

import argparse
import json
import re

from doxa.cli import _normalize_provider, _resolve_init_dest, build_parser, main
from doxa.cli import cmd_query
from doxa.config import load_config
from doxa.domains import domain_weights
from doxa.resources import banner_text
from doxa.schema import Belief, Quote, RetrievalResult, SourceRef


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def test_query_top_alias_sets_limit() -> None:
    args = build_parser().parse_args(["query", "self-reliance", "--top", "2"])
    assert args.limit == 2
    assert args.answer is False


def test_query_accepts_answer_flag() -> None:
    args = build_parser().parse_args(["query", "self-reliance", "--answer"])
    assert args.answer is True


def test_init_directory_path_targets_doxa_yaml() -> None:
    assert _resolve_init_dest("./").name == "doxa.yaml"


def test_fireworks_provider_alias_uses_openai_compatible() -> None:
    assert _normalize_provider("fireworks") == "openai-compatible"


def test_ingest_accepts_stdin_metadata_and_fetcher_override() -> None:
    args = build_parser().parse_args(
        [
            "ingest",
            "-",
            "--title",
            "Test",
            "--author",
            "Emerson",
            "--url",
            "https://example.com/test",
            "--via",
            "brightdata",
        ]
    )
    assert args.source == ["-"]
    assert args.title == "Test"
    assert args.author == "Emerson"
    assert args.url == "https://example.com/test"
    assert args.via == "brightdata"


def test_banner_command_prints_bundled_banner(capsys) -> None:
    code = main(["banner"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == banner_text()
    assert captured.err == ""


def test_banner_color_always_adds_ansi_without_changing_text(capsys) -> None:
    code = main(["banner", "--color", "always"])

    captured = capsys.readouterr()
    assert code == 0
    assert "\x1b[" in captured.out
    assert _strip_ansi(captured.out) == banner_text()
    assert captured.err == ""


def test_banner_no_color_alias_prints_plain_banner(capsys) -> None:
    code = main(["banner", "--no-color"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == banner_text()
    assert captured.err == ""


def test_query_accepts_domain_flags() -> None:
    args = build_parser().parse_args(
        ["query", "belief question", "--domain", "Technical", "--domains", "policy,creative", "--no-domain-boost"]
    )
    assert args.domain == ["Technical"]
    assert args.domains == "policy,creative"
    assert args.no_domain_boost is True


def _query_args(*, as_json: bool = False, answer: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        query="test question",
        config=None,
        search="keyword",
        limit=1,
        domain=[],
        domains="",
        no_domain_boost=False,
        json=as_json,
        answer=answer,
    )


def _retrieval_result() -> RetrievalResult:
    source = SourceRef(title="Test Source", author="Tester", date="2026")
    return RetrievalResult(
        belief=Belief(
            id="b1",
            belief="Raw belief text.",
            reasoning="Raw reasoning.",
            stance="supports",
            conviction=0.7,
            tags=[],
            source=source,
        ),
        quotes=[
            Quote(
                id="q1",
                quote="Exact quote text.",
                speaker="",
                source=source,
                context="",
                tags=[],
                belief_ids=["b1"],
            )
        ],
        score=0.5,
    )


def test_query_plain_output_stays_raw_without_answer(monkeypatch, capsys) -> None:
    result = _retrieval_result()
    monkeypatch.setattr("doxa.cli.load_config", lambda _: {})
    monkeypatch.setattr("doxa.cli.search", lambda *args, **kwargs: ([result], []))

    code = cmd_query(_query_args())

    output = capsys.readouterr().out
    assert code == 0
    assert "1. Raw belief text." in output
    assert "stance=supports conviction=0.70" in output
    assert "score=" not in output  # raw BM25 score is --json only, not human output
    assert 'quote="Exact quote text."' in output
    assert "The belief base points" not in output


def test_query_json_output_is_unchanged_by_answer_flag(monkeypatch, capsys) -> None:
    result = _retrieval_result()
    monkeypatch.setattr("doxa.cli.load_config", lambda _: {})
    monkeypatch.setattr("doxa.cli.search", lambda *args, **kwargs: ([result], []))

    code = cmd_query(_query_args(as_json=True, answer=True))

    output = capsys.readouterr().out
    assert code == 0
    assert json.loads(output) == [result.to_dict()]
    assert "The belief base points" not in output


def test_domains_without_subcommand_shows_chart() -> None:
    args = build_parser().parse_args(["domains"])
    assert args.domain_command is None
    assert args.func.__name__ == "cmd_domains"


def test_domains_set_accepts_config_after_subcommand(tmp_path) -> None:
    config_path = tmp_path / "doxa.yaml"
    code = main(["domains", "set", "technical", "8", "--config", str(config_path)])

    assert code == 0
    config = load_config(config_path, allow_demo_default=False)
    assert domain_weights(config)["technical"] == 8


def test_domains_set_accepts_config_before_subcommand(tmp_path) -> None:
    config_path = tmp_path / "doxa.yaml"
    code = main(["domains", "--config", str(config_path), "set", "technical", "8"])

    assert code == 0
    config = load_config(config_path, allow_demo_default=False)
    assert domain_weights(config)["technical"] == 8


def test_bare_invocation_shows_human_landing(capsys) -> None:
    code = main([])
    out = capsys.readouterr().out
    assert code == 0
    # banner + curated "start here", not a raw argparse dump
    assert "doxa demo" in out
    assert "doxa init" in out
    assert "skill install" in out


def test_guide_command_prints_walkthrough(capsys) -> None:
    code = main(["guide"])
    out = capsys.readouterr().out
    assert code == 0
    assert "no quote, no claim" in out
    assert "THE LOOP" in out


def test_status_reports_counts_for_a_config(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doxa.yaml").write_text("project:\n  name: t\n", encoding="utf-8")
    code = main(["status"])
    out = capsys.readouterr().out
    assert code == 0
    assert "config:" in out
    assert "beliefs:   0" in out


def test_missing_config_is_friendly_not_a_traceback(capsys, tmp_path) -> None:
    code = main(["query", "x", "--config", str(tmp_path / "none.yaml")])
    cap = capsys.readouterr()
    assert code == 2
    assert "Config not found" in cap.err
    assert "hint:" in cap.err
    assert "Traceback" not in cap.err
    assert cap.out == ""


def test_query_demo_notice_is_on_stderr_only(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # no doxa.yaml here -> demo fallback
    code = main(["query", "self-reliance"])
    cap = capsys.readouterr()
    assert code == 0
    assert "note:" in cap.err          # the "using demo" notice
    assert "note:" not in cap.out      # stdout stays clean for piping/agents
    assert "Emerson" in cap.out        # real demo result still printed


def test_query_json_has_no_human_notices(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["query", "self-reliance", "--json"])
    cap = capsys.readouterr()
    assert code == 0
    assert "note:" not in cap.out and "note:" not in cap.err
    json.loads(cap.out)  # pure, parseable JSON


def test_query_human_output_omits_raw_score(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["query", "self-reliance"])
    out = capsys.readouterr().out
    assert code == 0
    assert "conviction=" in out
    assert "score=" not in out  # raw BM25 score is --json only


def test_eval_leads_with_verdict(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # demo base is internally consistent
    code = main(["eval"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0] == "PASS"


def _populated_config(tmp_path):
    from doxa.config import load_config
    from doxa.schema import Belief, Quote, SourceRecord, SourceRef
    from doxa.store import JsonlStore

    (tmp_path / "doxa.yaml").write_text("project:\n  name: t\n", encoding="utf-8")
    cfg = str(tmp_path / "doxa.yaml")
    config = load_config(cfg, allow_demo_default=False)
    store = JsonlStore(config)
    ref = SourceRef(title="Essay", author="A", date="2026", url="https://x/e")
    src = SourceRecord(id="src1", title="Essay", author="A", date="2026", url="https://x/e", path="", text="Trust thyself.")
    belief = Belief(id="b1", belief="Trust yourself.", reasoning="r", stance="supports", conviction=0.9, tags=[], source=ref)
    quote = Quote(id="q1", quote="Trust thyself.", speaker="", source=ref, context="", tags=[], belief_ids=["b1"])
    store.write_all([belief], [quote], [src])
    return cfg, store


def test_sources_list_shows_ingested(capsys, tmp_path) -> None:
    cfg, _ = _populated_config(tmp_path)
    code = main(["sources", "list", "--config", cfg])
    out = capsys.readouterr().out
    assert code == 0
    assert "src1" in out and "Essay" in out
    assert "beliefs 1" in out and "quotes 1" in out


def test_sources_remove_deletes_source_and_rows(capsys, tmp_path) -> None:
    cfg, store = _populated_config(tmp_path)
    code = main(["sources", "remove", "src1", "--config", cfg])
    assert code == 0
    assert store.sources() == []
    assert store.beliefs() == []
    assert store.quotes() == []


def test_ingest_skips_duplicate_then_reingest_replaces(capsys, tmp_path, monkeypatch) -> None:
    from doxa import cli as cli_mod
    from doxa.mine import MiningResult
    from doxa.schema import Belief, Quote, SourceRecord, SourceRef

    (tmp_path / "doxa.yaml").write_text("project:\n  name: t\n", encoding="utf-8")
    cfg = str(tmp_path / "doxa.yaml")
    ref = SourceRef(title="Essay", url="https://x/e")
    src = SourceRecord(id="src1", title="Essay", author="", date="", url="https://x/e", path="", text="Trust thyself.")
    monkeypatch.setattr(cli_mod, "load_source", lambda *a, **k: src)

    def fake_mine(source, config, **kwargs):
        b = Belief(id="b1", belief="Trust yourself.", reasoning="r", stance="supports", conviction=0.9, source=ref)
        q = Quote(id="q1", quote="Trust thyself.", speaker="", source=ref, context="", belief_ids=["b1"])
        return MiningResult(beliefs=[b], quotes=[q])

    monkeypatch.setattr(cli_mod, "mine_source", fake_mine)

    assert main(["ingest", "ignored", "--config", cfg]) == 0
    store = cli_mod.JsonlStore(cli_mod.load_config(cfg, allow_demo_default=False))
    assert len(store.beliefs()) == 1

    capsys.readouterr()
    assert main(["ingest", "ignored", "--config", cfg]) == 0  # duplicate -> skipped
    assert len(store.beliefs()) == 1  # not doubled
    assert "already ingested" in capsys.readouterr().err

    assert main(["ingest", "ignored", "--config", cfg, "--reingest"]) == 0
    assert len(store.beliefs()) == 1  # replaced, not appended


def test_mine_source_dedupes_beliefs_across_chunks(monkeypatch) -> None:
    import json as _json
    from copy import deepcopy
    from doxa import mine as mine_mod
    from doxa.config import DEFAULT_CONFIG
    from doxa.schema import SourceRecord

    text = "Trust thyself. " * 2000  # > 12000 chars -> multiple chunks
    src = SourceRecord(id="s1", title="T", author="", date="", url="", path="", text=text)

    class FakeProvider:
        def complete(self, system, user):
            return _json.dumps(
                {
                    "beliefs": [{"id": "b1", "belief": "Trust yourself.", "reasoning": "r", "stance": "supports", "conviction": 0.9}],
                    "quotes": [{"id": "q1", "quote": "Trust thyself.", "speaker": "", "context": "", "belief_ids": ["b1"]}],
                }
            )

    monkeypatch.setattr(mine_mod, "get_provider", lambda config: FakeProvider())
    result = mine_mod.mine_source(src, deepcopy(DEFAULT_CONFIG))
    assert len(result.beliefs) == 1  # same belief restated per chunk collapses to one
