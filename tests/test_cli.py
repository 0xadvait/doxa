from __future__ import annotations

from doxa.cli import _normalize_provider, _resolve_init_dest, build_parser, main
from doxa.config import load_config
from doxa.domains import domain_weights


def test_query_top_alias_sets_limit() -> None:
    args = build_parser().parse_args(["query", "self-reliance", "--top", "2"])
    assert args.limit == 2


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


def test_query_accepts_domain_flags() -> None:
    args = build_parser().parse_args(
        ["query", "belief question", "--domain", "Technical", "--domains", "policy,creative", "--no-domain-boost"]
    )
    assert args.domain == ["Technical"]
    assert args.domains == "policy,creative"
    assert args.no_domain_boost is True


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
