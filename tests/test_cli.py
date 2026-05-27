from __future__ import annotations

from doxa.cli import _normalize_provider, _resolve_init_dest, build_parser


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
