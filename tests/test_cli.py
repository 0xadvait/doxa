from __future__ import annotations

import argparse
import json

from doxa.cli import _normalize_provider, _resolve_init_dest, build_parser, main
from doxa.cli import cmd_query
from doxa.config import load_config
from doxa.domains import domain_weights
from doxa.resources import banner_text
from doxa.schema import Belief, Quote, RetrievalResult, SourceRef


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
    assert args.source == "-"
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
    assert "stance=supports conviction=0.70 score=0.5000" in output
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
