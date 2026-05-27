"""Command line interface for doxa."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG, PROJECT_ROOT, data_dir, load_config
from .eval import faithfulness_report
from .mine import mine_source
from .retrieve import search
from .schema import DoxaError, RetrievalResult
from .sources import load_source
from .store import JsonlStore, index_postgres


FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "codex-cli": {
        "model": "",
        "api_key_env": "",
        "base_url": "",
    },
    "claude-cli": {
        "model": "",
        "api_key_env": "",
        "base_url": "",
    },
    "openai": {
        "model": "gpt-4.1-mini",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "",
    },
    "openai-compatible": {
        "model": "accounts/fireworks/models/kimi-k2p6",
        "api_key_env": "FIREWORKS_API_KEY",
        "base_url": FIREWORKS_BASE_URL,
    },
    "anthropic": {
        "model": "claude-3-5-sonnet-latest",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "",
    },
}

PROVIDER_ALIASES = {
    "codex": "codex-cli",
    "codex-cli": "codex-cli",
    "claude": "claude-cli",
    "claude-cli": "claude-cli",
    "openai": "openai",
    "openai-compatible": "openai-compatible",
    "openai-compatible/fireworks": "openai-compatible",
    "fireworks": "openai-compatible",
    "anthropic": "anthropic",
}

DEFAULT_LENS = {
    "name": "durable-beliefs",
    "description": "Extract durable claims, values, and stances that the source explicitly supports.",
    "question": "What does this source believe about how people should think, decide, or act?",
}


def _print_error(exc: Exception) -> int:
    print(f"error: {exc}", file=sys.stderr)
    return 2


def _resolve_init_dest(path: str) -> Path:
    raw_path = path or "doxa.yaml"
    expanded = Path(raw_path).expanduser()
    if expanded.exists() and expanded.is_dir():
        return expanded / "doxa.yaml"
    if raw_path.endswith(("/", "\\")):
        return expanded / "doxa.yaml"
    return expanded


def _normalize_provider(provider: str | None) -> str:
    raw = (provider or "codex-cli").strip().lower()
    normalized = PROVIDER_ALIASES.get(raw)
    if not normalized:
        choices = ", ".join(PROVIDER_DEFAULTS)
        raise DoxaError(f"Unknown provider '{provider}'. Use one of: {choices}.")
    return normalized


def _prompt_text(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else " [optional]"
    try:
        value = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def _prompt_provider(default: str) -> str:
    options = [
        ("codex-cli", "codex-cli (default, no API key; uses Codex CLI auth)"),
        ("claude-cli", "claude-cli (no API key; uses Claude Code auth)"),
        ("openai", "openai (uses OPENAI_API_KEY by default)"),
        ("openai-compatible", "openai-compatible / Fireworks"),
        ("anthropic", "anthropic (uses ANTHROPIC_API_KEY by default)"),
    ]
    print("How do you want to mine beliefs?")
    for index, (_, label) in enumerate(options, start=1):
        print(f"  {index}. {label}")
    raw = _prompt_text("Provider number or name", default)
    if raw.isdigit():
        choice_index = int(raw) - 1
        if 0 <= choice_index < len(options):
            return options[choice_index][0]
    return _normalize_provider(raw)


def _init_answers(args: argparse.Namespace, *, interactive: bool) -> dict[str, str]:
    provider_default = _normalize_provider(args.provider)
    provider = _prompt_provider(provider_default) if interactive else provider_default
    defaults = PROVIDER_DEFAULTS[provider]

    model_default = args.model if args.model is not None else defaults["model"]
    if interactive:
        if provider in {"codex-cli", "claude-cli"}:
            print("Model is optional for this CLI provider; leave it blank to let the CLI decide.")
        elif provider == "openai-compatible":
            print("Fireworks model names look like: accounts/fireworks/models/<slug>")
        model = _prompt_text("Model", model_default)
    else:
        model = model_default

    api_key_env = args.api_key_env or defaults["api_key_env"]
    base_url = args.base_url if args.base_url is not None else defaults["base_url"]
    if interactive and provider in {"openai", "openai-compatible", "anthropic"}:
        api_key_env = _prompt_text("API key environment variable", api_key_env)
        if provider == "openai-compatible":
            base_url = _prompt_text("OpenAI-compatible base_url", base_url)

    lens_name_default = args.lens_name or DEFAULT_LENS["name"]
    lens_description_default = args.lens or DEFAULT_LENS["description"]
    lens_question_default = args.lens_question or DEFAULT_LENS["question"]
    if interactive:
        print("Now define the lens: what kind of beliefs should doxa mine?")
        lens_name = _prompt_text("Lens name", lens_name_default)
        lens_description = _prompt_text("Lens description", lens_description_default)
        lens_question = _prompt_text("Guiding question", lens_question_default)
    else:
        lens_name = lens_name_default
        lens_description = lens_description_default
        lens_question = lens_question_default

    return {
        "provider": provider,
        "model": model,
        "api_key_env": api_key_env,
        "base_url": base_url,
        "lens_name": lens_name,
        "lens_description": lens_description,
        "lens_question": lens_question,
    }


def _build_init_config(answers: dict[str, str]) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    provider = answers["provider"]
    model = answers["model"]
    config["project"]["name"] = "my-belief-base"
    config["lens"] = {
        "name": answers["lens_name"],
        "description": answers["lens_description"],
        "question": answers["lens_question"],
        "stances": ["supports", "questions", "rejects", "complicates"],
        "tags": [],
    }
    config["llm"]["provider"] = provider
    config["llm"]["model"] = model
    provider_config = config["providers"].get(provider)
    if provider_config is not None:
        if model and "model" in provider_config:
            provider_config["model"] = model
        if answers["api_key_env"] and "api_key_env" in provider_config:
            provider_config["api_key_env"] = answers["api_key_env"]
        if provider == "openai-compatible":
            provider_config["base_url"] = answers["base_url"]
    return config


def _write_yaml_config(dest: Path, config: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - pyyaml is a core dependency
        raise DoxaError("Missing dependency: install pyyaml or reinstall doxa with core dependencies.") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = "# doxa configuration\n# Generated by `doxa init`. Paths are relative to this file.\n\n"
    dest.write_text(header + yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    dest = _resolve_init_dest(args.path)
    if dest.exists() and not args.force:
        raise DoxaError(f"{dest} already exists. Use --force to overwrite.")
    interactive = not (args.yes or args.non_interactive) and sys.stdin.isatty()
    if interactive:
        print("doxa init: configure belief mining")
        print("Press Enter to accept any default.")
    answers = _init_answers(args, interactive=interactive)
    _write_yaml_config(dest, _build_init_config(answers))
    config = load_config(dest, allow_demo_default=False)
    data_dir(config).mkdir(parents=True, exist_ok=True)
    print(f"Created {dest}")
    print(f"Data directory: {data_dir(config)}")
    print(f"Provider: {answers['provider']}")
    if answers["model"]:
        print(f"Model: {answers['model']}")
    if answers["api_key_env"]:
        print(f"API key env: {answers['api_key_env']}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    config = load_config(args.config, allow_demo_default=False)
    stdin_text = sys.stdin.read() if args.source == "-" else None
    source = load_source(
        args.source,
        config=config,
        via=args.via,
        stdin_text=stdin_text,
        title=args.title or "",
        author=args.author or "",
        url=args.url or "",
    )
    result = mine_source(source, config)
    store = JsonlStore(config)
    store.append(result.beliefs, result.quotes, [source])
    print(f"Ingested: {source.title}")
    print(f"Beliefs written: {len(result.beliefs)}")
    print(f"Quotes written: {len(result.quotes)}")
    if result.dropped_quotes:
        print(f"Dropped unverifiable quotes: {len(result.dropped_quotes)}")
    if result.dropped_beliefs:
        print(f"Dropped unanchored beliefs: {len(result.dropped_beliefs)}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    counts = index_postgres(config)
    print(f"Indexed {counts['beliefs']} beliefs and {counts['quotes']} quotes into Postgres/pgvector.")
    return 0


def _format_result(result: RetrievalResult, index: int) -> str:
    lines = [
        f"{index}. {result.belief.belief}",
        f"   stance={result.belief.stance} conviction={result.belief.conviction:.2f} score={result.score:.4f}",
        f"   source={result.belief.source.title} / {result.belief.source.author} / {result.belief.source.date}",
    ]
    for quote in result.quotes:
        speaker = f"{quote.speaker}: " if quote.speaker else ""
        lines.append(f'   quote="{speaker}{quote.quote}"')
    return "\n".join(lines)


def cmd_query(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    results, warnings = search(args.query, config, search_type=args.search, limit=args.limit)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps([result.to_dict() for result in results], indent=2, ensure_ascii=False))
        return 0
    if not results:
        print("No matching beliefs found.")
        return 0
    for index, result in enumerate(results, start=1):
        print(_format_result(result, index))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    report = faithfulness_report(config)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Beliefs: {report['beliefs']}")
        print(f"Quotes: {report['quotes']}")
        print(f"Sources: {report['sources']}")
        print(f"Checked quotes: {report['checked_quotes']}")
        print(f"Quote verbatim: {report['quote_verbatim_percent']:.2f}%")
        print(f"Bad links: {len(report['bad_links'])}")
        print(f"Orphan beliefs: {len(report['orphan_beliefs'])}")
        print(f"OK: {report['ok']}")
    return 0 if report["ok"] else 1


def cmd_demo(args: argparse.Namespace) -> int:
    demo_config = load_config(PROJECT_ROOT / "examples" / "demo" / "doxa.yaml", allow_demo_default=False)
    demo_data = data_dir(demo_config)
    store = JsonlStore(demo_config)
    beliefs = store.beliefs()
    quotes = store.quotes()
    print("doxa public-domain demo")
    print(f"Data: {demo_data}")
    print(f"Beliefs: {len(beliefs)}")
    print(f"Quotes: {len(quotes)}")
    print('Try: doxa query "self-reliance and conformity" --search keyword')
    if args.query:
        results, warnings = search(args.query, demo_config, search_type="keyword", limit=args.limit)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        print("")
        print(f"Sample query: {args.query}")
        for index, result in enumerate(results, start=1):
            print(_format_result(result, index))
    return 0


HARNESS_PATHS = {
    "claude-code": {
        "user": Path("~/.claude/skills/doxa"),
        "project": Path(".claude/skills/doxa"),
    },
    "codex": {
        "user": Path("~/.codex/skills/doxa"),
        "project": Path(".codex/skills/doxa"),
    },
    "hermes": {
        "user": Path("~/.hermes/skills/doxa"),
        "project": Path(".hermes/skills/doxa"),
    },
    "openclaw": {
        "user": Path("~/.openclaw/skills/doxa"),
        "project": Path(".openclaw/skills/doxa"),
    },
}


def _skill_source() -> Path:
    source = PROJECT_ROOT / "skill" / "SKILL.md"
    if not source.exists():
        raise DoxaError(f"Could not find bundled skill at {source}")
    return source


def cmd_skill_install(args: argparse.Namespace) -> int:
    if args.dest:
        dest_dir = Path(args.dest).expanduser()
    elif args.harness == "generic":
        dest_dir = Path("skills/doxa")
    else:
        mapping = HARNESS_PATHS.get(args.harness)
        if not mapping:
            raise DoxaError("Unknown harness path. Use --dest to choose an install directory.")
        dest_dir = mapping[args.scope].expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "SKILL.md"
    shutil.copyfile(_skill_source(), dest_file)
    print(f"Installed doxa skill: {dest_file}")
    if args.harness == "generic":
        print("Point your agent harness at that directory and ensure the `doxa` CLI is on PATH.")
    else:
        print(f"Harness: {args.harness} ({args.scope} scope)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doxa", description="Build and query a verbatim-grounded belief base.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a documented doxa.yaml config.")
    init.add_argument("path", nargs="?", default="doxa.yaml")
    init.add_argument("--force", action="store_true")
    init.add_argument("-y", "--yes", action="store_true", help="Use defaults and skip prompts.")
    init.add_argument("--non-interactive", action="store_true", help="Use defaults and skip prompts.")
    init.add_argument("--provider", help="codex-cli, claude-cli, openai, openai-compatible, fireworks, or anthropic.")
    init.add_argument("--model", help="Model name to write into llm.model.")
    init.add_argument("--api-key-env", help="Environment variable that holds the API provider key.")
    init.add_argument("--base-url", help="OpenAI-compatible base URL.")
    init.add_argument("--lens", help="Lens description.")
    init.add_argument("--lens-name", help="Lens name.")
    init.add_argument("--lens-question", help="Guiding question for the lens.")
    init.set_defaults(func=cmd_init)

    ingest = subparsers.add_parser("ingest", help="Ingest a text, PDF, URL, YouTube source, or '-' from stdin.")
    ingest.add_argument("source")
    ingest.add_argument("--config")
    ingest.add_argument("--title", help="Override title metadata for stdin/text sources.")
    ingest.add_argument("--author", help="Override author metadata for stdin/text sources.")
    ingest.add_argument("--url", help="Attach source URL metadata for stdin/text sources.")
    ingest.add_argument("--via", choices=["requests", "brightdata"], help="Override URL fetcher for this ingest.")
    ingest.set_defaults(func=cmd_ingest)

    index = subparsers.add_parser("index", help="Build optional Postgres/pgvector semantic index.")
    index.add_argument("--config")
    index.set_defaults(func=cmd_index)

    query = subparsers.add_parser("query", help="Query beliefs and linked verbatim quotes.")
    query.add_argument("query")
    query.add_argument("--config")
    query.add_argument("--search", choices=["keyword", "semantic", "hybrid"], default="keyword")
    query.add_argument("--limit", "--top", dest="limit", type=int, default=5)
    query.add_argument("--json", action="store_true")
    query.set_defaults(func=cmd_query)

    eval_parser = subparsers.add_parser("eval", help="Run faithfulness and link-integrity checks.")
    eval_parser.add_argument("--config")
    eval_parser.add_argument("--json", action="store_true")
    eval_parser.set_defaults(func=cmd_eval)

    demo = subparsers.add_parser("demo", help="Show bundled public-domain demo data.")
    demo.add_argument("--query", default="")
    demo.add_argument("--limit", type=int, default=3)
    demo.set_defaults(func=cmd_demo)

    skill = subparsers.add_parser("skill", help="Install or inspect the portable agent skill.")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    install = skill_sub.add_parser("install", help="Install skill/SKILL.md into an agent harness.")
    install.add_argument("--harness", default="generic", help="claude-code, codex, hermes, openclaw, generic, or a custom label with --dest")
    install.add_argument("--scope", choices=["user", "project"], default="user")
    install.add_argument("--dest")
    install.set_defaults(func=cmd_skill_install)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except DoxaError as exc:
        return _print_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
