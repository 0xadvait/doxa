"""Command line interface for doxa."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .answer import render_terminal_answer
from .banner import render_banner, should_use_color
from .config import DEFAULT_CONFIG, data_dir, load_config
from .guide import guide_text, overview_text
from .domains import (
    add_domain_weight,
    chart as domain_chart,
    domain_weights,
    edit_domain_weights,
    export_domain_weights,
    parse_domain_selectors,
    remove_domain_weight,
    reset_domain_weights,
    set_domain_weight,
)
from .eval import faithfulness_report
from .mine import mine_source
from .retrieve import search
from .lenses import (
    get_lens_template,
    lens_catalog,
    remove_user_lens,
    save_user_lens,
    template_to_config_lens,
    user_lens_dir,
)
from .resources import demo_config_path, skill_text
from .schema import DoxaError, RetrievalResult
from .sources import load_source
from .sources.fetchers import INGEST_MODES, available_fetchers, build_fetch_prompt
from .store import JsonlStore, index_postgres, postgres_table_prefix


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
    hint = _error_hint(exc)
    if hint:
        print(f"hint: {hint}", file=sys.stderr)
    return 2


def _error_hint(exc: Exception) -> str:
    """Map a raw error to one actionable next step, for humans at a prompt."""

    text = str(exc).lower()
    # Postgres / pgvector first (so 'database "x" does not exist' doesn't match the generic file branch)
    if "extension" in text and "vector" in text:
        return 'enable pgvector as a superuser/owner: psql "$DOXA_POSTGRES_DSN" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
    if any(s in text for s in ("connection to server", "could not connect", "could not translate host",
                               "connection refused", "password authentication", 'role "', 'database "')):
        return "check DOXA_POSTGRES_DSN points at a running Postgres (see `doxa status`); create the database/role if needed."
    if any(s in text for s in ("no such file", "does not exist", "not found", "cannot find")):
        if any(s in text for s in ("config", ".yaml", ".yml")):
            return "create one with `doxa init`, or point at it with --config <path>."
        return "check the path, or run `doxa demo` to try the bundled data."
    if any(s in text for s in ("api key", "api_key", "environment variable")):
        return "set the API key env var, or use a no-key provider: `doxa init --provider codex-cli`."
    if any(s in text for s in ("binary", "on path", "command not found", "executable")):
        return "install that provider's CLI, or switch providers with `doxa init`."
    if "yaml" in text:
        return "your doxa.yaml may be malformed; regenerate it with `doxa init --force`."
    return ""


def _hint(message: str) -> None:
    """Print a human-facing hint to stderr (kept off stdout so --json stays clean)."""

    sys.stdout.flush()
    print(message, file=sys.stderr)


def _stdout_color() -> bool:
    return should_use_color("auto", sys.stdout)


def _is_demo_fallback(config: dict[str, Any]) -> bool:
    """True when no user config was found and doxa fell back to bundled demo data."""

    return not config.get("_config_path")


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


def _lens_choice(raw: str, names: list[str]) -> str | None:
    """Map a picker input (number, name, or blank/'custom') to a template name, or None for custom."""
    raw = raw.strip()
    if not raw or raw.lower() in {"custom", "c"}:
        return None
    if raw.isdigit():
        index = int(raw) - 1
        return names[index] if 0 <= index < len(names) else None
    return raw if raw in names else None


def _prompt_lens() -> dict[str, Any]:
    """Interactive lens picker. Returns a chosen template dict, or {} for a custom lens."""
    catalog = lens_catalog()
    if not catalog:
        return {}
    names = [row["name"] for row in catalog]
    width = max(len(name) for name in names)
    print("\nPick a lens -- the question doxa asks of every source (this shapes every belief):")
    for index, row in enumerate(catalog, start=1):
        suffix = " (yours)" if row["origin"] == "user" else ""
        print(f"  {index}. {row['name'].ljust(width)}  {row['summary']}{suffix}")
    print(f"  {len(catalog) + 1}. {'custom'.ljust(width)}  define your own from scratch")
    default_name = "durable-beliefs" if "durable-beliefs" in names else names[0]
    name = _lens_choice(_prompt_text("Lens number or name", default_name), names)
    if name is None:
        return {}
    try:
        return get_lens_template(name)
    except DoxaError:
        return {}


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

    template = get_lens_template(args.lens_template) if getattr(args, "lens_template", None) else {}
    if interactive and not template:
        template = _prompt_lens()  # let the user pick from the library instead of inventing one
    lens_name_default = args.lens_name or template.get("name") or DEFAULT_LENS["name"]
    lens_description_default = args.lens or template.get("description") or DEFAULT_LENS["description"]
    lens_question_default = args.lens_question or template.get("question") or DEFAULT_LENS["question"]
    lens_stances = template.get("stances") or ["supports", "questions", "rejects", "complicates"]
    lens_tags = template.get("tags") or []
    if interactive:
        if template:
            print(f"\nUsing the '{template.get('name')}' lens -- press Enter to keep each field, or edit it:")
        else:
            print("\nDefine a custom lens: what kind of beliefs should doxa mine?")
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
        "lens_stances": lens_stances,
        "lens_tags": lens_tags,
    }


def _build_init_config(answers: dict[str, str], *, full: bool = False) -> dict[str, Any]:
    if full:
        config: dict[str, Any] = deepcopy(DEFAULT_CONFIG)
    else:
        config = {
            "project": {"name": "my-belief-base"},
            "data": {"dir": "data"},
            "lens": {},
            "llm": {"provider": answers["provider"], "model": answers["model"], "temperature": 0},
            "providers": {answers["provider"]: deepcopy(DEFAULT_CONFIG["providers"].get(answers["provider"], {}))},
        }
    provider = answers["provider"]
    model = answers["model"]
    config["project"]["name"] = "my-belief-base"
    config["lens"] = {
        "name": answers["lens_name"],
        "description": answers["lens_description"],
        "question": answers["lens_question"],
        "stances": answers.get("lens_stances") or ["supports", "questions", "rejects", "complicates"],
        "tags": answers.get("lens_tags") or [],
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
    _write_yaml_config(dest, _build_init_config(answers, full=args.full))
    config = load_config(dest, allow_demo_default=False)
    data_dir(config).mkdir(parents=True, exist_ok=True)
    print(f"Created {dest}")
    print(f"Data directory: {data_dir(config)}")
    print(f"Provider: {answers['provider']}")
    if answers["model"]:
        print(f"Model: {answers['model']}")
    if getattr(args, "lens_template", None):
        print(f"Lens template: {args.lens_template}")
    print(f"Lens: {answers['lens_name']}")
    if answers["api_key_env"]:
        print(f"API key env: {answers['api_key_env']}")

    in_cwd = dest.name in ("doxa.yaml", "doxa.yml") and dest.resolve().parent == Path.cwd().resolve()
    cfg = "" if in_cwd else f" --config {dest}"
    print("")
    print("Next steps:")
    if answers["api_key_env"]:
        print(f"  0. export {answers['api_key_env']}=...           set your provider API key")
    print(f"  1. doxa ingest <file|url|->{cfg}      mine your first source")
    print(f'  2. doxa query "<question>"{cfg}       ask -- answers cite verbatim quotes')
    print("  (new to doxa? run `doxa guide` for the full walkthrough.)")
    return 0


def _mining_progress(title: str):
    """A progress callback for mine_source: a live chunk counter on stderr.

    Mining calls an LLM per chunk and can take minutes; without this the CLI looks
    frozen. On a non-TTY we print one static line instead of a redrawing counter.
    """
    if not sys.stderr.isatty():
        print(f"Mining {title} ...", file=sys.stderr, flush=True)
        return None

    def cb(index: int, total: int) -> None:
        sys.stderr.write(f"\r  mining {title}: chunk {index}/{total} ...")
        sys.stderr.flush()
        if index == total:
            sys.stderr.write("\r" + " " * (len(title) + 36) + "\r")
            sys.stderr.flush()

    return cb


def _apply_yolo(config: dict[str, Any]) -> None:
    """doxa's yolo mode: let agent/command fetchers run unattended for this ingest --
    codex bypass-approvals, hermes --yolo, and the command shell. Trusted sources only."""
    sources = config.setdefault("sources", {})
    sources.setdefault("codex", {})["unsafe_bypass"] = True
    sources.setdefault("hermes", {})["unsafe_yolo"] = True
    sources.setdefault("command", {})["allow_shell"] = True


def cmd_ingest(args: argparse.Namespace) -> int:
    config = load_config(args.config, allow_demo_default=False)
    if getattr(args, "yolo", False):
        _apply_yolo(config)
        _hint("yolo: agent fetchers run with bypass/--yolo + shell enabled for this ingest -- trusted sources only.")
    store = JsonlStore(config)
    source_args = args.source if isinstance(args.source, list) else [args.source]
    stdin_text = sys.stdin.read() if "-" in source_args else None

    fetch_prompt = build_fetch_prompt(getattr(args, "mode", None), getattr(args, "prompt", None))
    if fetch_prompt:
        effective_fetcher = args.via or (config.get("sources", {}).get("fetcher") or "requests")
        if effective_fetcher not in {"claude", "codex", "hermes", "command"}:
            _hint(f"note: --prompt/--mode only affect agent/command fetchers; '{effective_fetcher}' ignores them (try `--via hermes`).")

    total_b = total_q = ingested = skipped = 0
    for src in source_args:
        source = load_source(
            src,
            config=config,
            via=args.via,
            stdin_text=stdin_text if src == "-" else None,
            title=args.title or "",
            author=args.author or "",
            url=args.url or "",
            fetch_prompt=fetch_prompt,
        )
        if not source.text.strip():
            _hint(f"skipped {source.title}: no extractable text (scanned PDF needs OCR; empty file has nothing to mine).")
            skipped += 1
            continue
        if store.has_source(source.id):
            if not args.reingest:
                _hint(f"skipped {source.title}: already ingested. Re-run with --reingest to replace it.")
                skipped += 1
                continue
            removed = store.remove_source(source.id)
            _hint(f"re-ingesting {source.title} (removed {removed['beliefs']} old beliefs, {removed['quotes']} quotes).")

        result = mine_source(source, config, progress=_mining_progress(source.title))
        store.append(result.beliefs, result.quotes, [source])
        ingested += 1
        total_b += len(result.beliefs)
        total_q += len(result.quotes)

        line = f"Ingested: {source.title}\n  beliefs {len(result.beliefs)} · quotes {len(result.quotes)}"
        dropped = []
        if result.dropped_quotes:
            dropped.append(f"{len(result.dropped_quotes)} quotes not verbatim")
        if result.dropped_beliefs:
            dropped.append(f"{len(result.dropped_beliefs)} beliefs unanchored")
        if dropped:
            line += "  (dropped: " + "; ".join(dropped) + ")"
        print(line)
        if not result.beliefs:
            _hint(f"note: 0 beliefs from {source.title} -- the lens matched nothing; adjust it via `doxa init`.")

    if len(source_args) > 1:
        print(f"Done: {ingested} ingested, {skipped} skipped. Added {total_b} beliefs, {total_q} quotes.")
    if ingested and sys.stdout.isatty():
        _hint('Next: doxa query "<question>"   |   doxa eval   |   doxa status')
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if _is_demo_fallback(config):
        _hint("note: no doxa.yaml here -- indexing the bundled demo base. Run `doxa init` to build your own.")
    counts = index_postgres(config)
    print(f"Indexed {counts['beliefs']} beliefs and {counts['quotes']} quotes into Postgres/pgvector.")
    return 0


def _format_result(result: RetrievalResult, index: int) -> str:
    lines = [
        f"{index}. {result.belief.belief}",
        f"   stance={result.belief.stance} conviction={result.belief.conviction:.2f}",
        f"   source={result.belief.source.title} / {result.belief.source.author} / {result.belief.source.date}",
    ]
    for quote in result.quotes:
        speaker = f"{quote.speaker}: " if quote.speaker else ""
        lines.append(f'   quote="{speaker}{quote.quote}"')
    return "\n".join(lines)


def _store_has_beliefs(config: dict[str, Any]) -> bool:
    try:
        return bool(JsonlStore(config).beliefs())
    except Exception:  # noqa: BLE001 - if unsure, don't claim the base is empty
        return True


def cmd_query(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if not args.json and _is_demo_fallback(config):
        _hint("note: no doxa.yaml here -- querying the bundled demo base. Run `doxa init` to build your own.")
    domains = parse_domain_selectors(args.domain, args.domains)
    results, warnings = search(
        args.query,
        config,
        search_type=args.search,
        limit=args.limit,
        domains=domains,
        domain_boost=not args.no_domain_boost,
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps([result.to_dict() for result in results], indent=2, ensure_ascii=False))
        return 0
    if not results:
        print("No matching beliefs found.")
        if not args.json:
            if not _is_demo_fallback(config) and not _store_has_beliefs(config):
                _hint("hint: your belief base is empty -- ingest a source: doxa ingest <file|url|->   (or try `doxa demo`).")
            else:
                _hint("hint: try broader terms, raise --top, or --search hybrid if you've run `doxa index`.")
        return 0
    if args.answer:
        print(render_terminal_answer(args.query, results))
        return 0
    for index, result in enumerate(results, start=1):
        print(_format_result(result, index))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if not args.json and _is_demo_fallback(config):
        _hint("note: no doxa.yaml here -- evaluating the bundled demo base.")
    report = faithfulness_report(config)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 1
    ok = report["ok"]
    print("PASS" if ok else "FAIL")
    print(f"  beliefs {report['beliefs']} · quotes {report['quotes']} · sources {report['sources']}")
    print(f"  quote verbatim: {report['quote_verbatim_percent']:.2f}%  ({report['checked_quotes']} checked)")
    if ok:
        print("  every quote is verbatim and every belief is linked.")
    else:
        def _ids(rows: list, key: str | None = None) -> str:
            vals = [str(r[key]) if key else str(r) for r in rows[:10]]
            return ", ".join(vals) + (" ..." if len(rows) > 10 else "")

        if report["invalid_quotes"]:
            print(f"  non-verbatim quotes ({len(report['invalid_quotes'])}): {_ids(report['invalid_quotes'], 'id')}")
        if report["bad_links"]:
            print(f"  broken belief links ({len(report['bad_links'])}): {_ids(report['bad_links'], 'quote_id')}")
        if report["orphan_beliefs"]:
            print(f"  orphan beliefs ({len(report['orphan_beliefs'])}): {_ids(report['orphan_beliefs'])}")
        _hint("hint: fix or remove the listed rows in data/*.jsonl (or re-ingest the source), then re-run `doxa eval`.")
    return 0 if ok else 1


def cmd_demo(args: argparse.Namespace) -> int:
    demo_config = load_config(demo_config_path(), allow_demo_default=False)
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


def cmd_banner(args: argparse.Namespace) -> int:
    sys.stdout.write(render_banner(color=args.color, stream=sys.stdout))
    return 0


def cmd_guide(args: argparse.Namespace) -> int:
    print(guide_text(color=_stdout_color()))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(getattr(args, "config", None))
    store = JsonlStore(config)
    try:
        n_beliefs, n_quotes, n_sources = len(store.beliefs()), len(store.quotes()), len(store.sources())
    except Exception:  # noqa: BLE001 - a broken/missing store should still print a status
        n_beliefs = n_quotes = n_sources = 0
    llm = config.get("llm", {})
    cfg_path = config.get("_config_path") or "(none -- using bundled demo)"
    print(f"config:    {cfg_path}")
    print(f"data dir:  {data_dir(config)}")
    print(f"beliefs:   {n_beliefs}")
    print(f"quotes:    {n_quotes}")
    print(f"sources:   {n_sources}")
    print(f"provider:  {llm.get('provider', '?')}  (model: {llm.get('model') or 'provider default'})")
    dsn_env = config.get("postgres", {}).get("dsn_env", "DOXA_POSTGRES_DSN")
    print(f"semantic:  {'ready' if os.environ.get(dsn_env) else f'off (set {dsn_env}, then doxa index)'}")
    print(f"fetcher:   {config.get('sources', {}).get('fetcher', 'requests')}")
    if _is_demo_fallback(config):
        _hint("note: no doxa.yaml here -- run `doxa init` to start your own belief base.")
    elif n_beliefs == 0:
        _hint("hint: your base is empty -- ingest a source: doxa ingest <file|url|->")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check common local setup problems without mining or fetching anything."""

    issues: list[str] = []
    try:
        config = load_config(getattr(args, "config", None), allow_demo_default=False)
    except Exception as exc:
        print(f"config: FAIL ({exc})")
        return 1
    print(f"config: OK ({config.get('_config_path') or 'defaults'})")
    try:
        postgres_table_prefix(config)
        print("postgres table prefix: OK")
    except Exception as exc:
        issues.append(f"postgres table prefix: {exc}")
        print(f"postgres table prefix: FAIL ({exc})")
    store = JsonlStore(config)
    try:
        counts = (len(store.beliefs()), len(store.quotes()), len(store.sources()))
        print(f"store: OK ({counts[0]} beliefs, {counts[1]} quotes, {counts[2]} sources)")
    except Exception as exc:
        issues.append(f"store: {exc}")
        print(f"store: FAIL ({exc})")
    provider = str((config.get("llm") or {}).get("provider") or "codex-cli")
    provider_config = (config.get("providers") or {}).get(provider, {})
    if provider in {"codex-cli", "claude-cli"}:
        binary = str(provider_config.get("binary") or ("codex" if provider == "codex-cli" else "claude"))
        if shutil.which(binary):
            print(f"provider: OK ({provider}, binary {binary})")
        else:
            issues.append(f"provider binary not found: {binary}")
            print(f"provider: FAIL ({provider} binary not found: {binary})")
    else:
        api_key_env = str(provider_config.get("api_key_env") or "")
        if api_key_env and not os.environ.get(api_key_env):
            issues.append(f"provider env var not set: {api_key_env}")
            print(f"provider: FAIL ({provider}, set {api_key_env})")
        else:
            print(f"provider: OK ({provider})")
    dsn_env = str((config.get("postgres") or {}).get("dsn_env") or "DOXA_POSTGRES_DSN")
    print(f"semantic index: {'configured' if os.environ.get(dsn_env) else f'off (set {dsn_env} to enable)'}")
    if issues:
        print("\nDoctor found issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("\nDoctor found no blocking issues.")
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    command = getattr(args, "sources_command", None) or "list"
    config = load_config(getattr(args, "config", None))
    store = JsonlStore(config)
    if command == "remove":
        removed = store.remove_source(args.id)
        print(f"Removed {args.id}: -{removed['beliefs']} beliefs, -{removed['quotes']} quotes, -1 source.")
        return 0
    # list
    if _is_demo_fallback(config):
        _hint("note: no doxa.yaml here -- showing the bundled demo base.")
    sources = store.sources()
    if not sources:
        print("No sources ingested yet.")
        _hint("add one: doxa ingest <file|url|->")
        return 0
    beliefs = store.beliefs()
    quotes = store.quotes()

    def source_matches(ref, source) -> bool:
        if getattr(ref, "id", ""):
            return ref.id == source.id
        return (ref.title, ref.url) == (source.title, source.url)

    print(f"{len(sources)} source(s):")
    for source in sources:
        belief_count = sum(1 for belief in beliefs if source_matches(belief.source, source))
        quote_count = sum(1 for quote in quotes if source_matches(quote.source, source))
        print(f"  {source.id}  {source.title}  [beliefs {belief_count}, quotes {quote_count}]")
        location = source.url or source.path
        if location:
            print(f"      {location}")
    _hint("remove one with: doxa sources remove <id>")
    return 0


def cmd_domains(args: argparse.Namespace) -> int:
    command = getattr(args, "domain_command", None) or "view"
    config_path = getattr(args, "config", None)
    if command == "view":
        config = load_config(config_path, allow_demo_default=False)
        print(domain_chart(domain_weights(config)))
        return 0
    if command == "export":
        config = load_config(config_path, allow_demo_default=False)
        print(export_domain_weights(domain_weights(config), as_json=args.json))
        return 0
    if command == "set":
        path = set_domain_weight(config_path, args.slug, args.weight)
    elif command == "add":
        path = add_domain_weight(config_path, args.slug, args.weight)
    elif command == "remove":
        path = remove_domain_weight(config_path, args.slug)
    elif command == "reset":
        path = reset_domain_weights(config_path)
    elif command == "edit":
        path = edit_domain_weights(config_path)
    else:  # pragma: no cover - argparse constrains this
        raise DoxaError(f"Unknown domains command: {command}")
    print(f"Updated domain preferences: {path}")
    config = load_config(path, allow_demo_default=False)
    print(domain_chart(domain_weights(config)))
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
    dest_file.write_text(skill_text(), encoding="utf-8")
    print(f"Installed doxa skill: {dest_file}")
    if args.harness == "generic":
        print("Point your agent harness at that directory and ensure the `doxa` CLI is on PATH.")
    else:
        print(f"Harness: {args.harness} ({args.scope} scope)")
    return 0


def cmd_lenses_list(args: argparse.Namespace) -> int:
    catalog = lens_catalog()
    if not catalog:
        print("No lens templates found.")
        return 0
    width = max(len(row["name"]) for row in catalog)
    print("Lens templates -- start here instead of inventing a lens:\n")
    for row in catalog:
        suffix = "  (yours)" if row["origin"] == "user" else ""
        print(f"  {row['name'].ljust(width)}  {row['summary']}{suffix}")
    print("\nShow one:    doxa lenses show <name>")
    print("Use one:     doxa init --lens-template <name>")
    print("Make one:    doxa lenses add <name> --from <name>")
    print(f"Your lenses: {user_lens_dir()}")
    return 0


def cmd_lenses_show(args: argparse.Namespace) -> int:
    import yaml

    template = get_lens_template(args.name)
    print(f"# lens template: {args.name}")
    if template.get("summary"):
        print(f"# {template['summary']}")
    print()
    print(yaml.safe_dump({"lens": template_to_config_lens(template)}, sort_keys=False, allow_unicode=True).rstrip())
    print()
    print(f"Use it:  doxa init --lens-template {args.name}")
    print(f"Fork it: doxa lenses add my-{args.name} --from {args.name}")
    return 0


def cmd_lenses_add(args: argparse.Namespace) -> int:
    if args.file:
        import yaml

        template = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or {}
        if not isinstance(template, dict):
            raise DoxaError("lens file must be a YAML mapping")
    elif args.from_template:
        template = dict(get_lens_template(args.from_template))
    else:
        template = {}
    if args.summary:
        template["summary"] = args.summary
    if args.description:
        template["description"] = args.description
    if args.question:
        template["question"] = args.question
    if not template.get("description"):
        raise DoxaError("a lens needs a description -- pass --from <template>, --file <yaml>, or --description")
    path = save_user_lens(args.name, template)
    print(f"Saved lens '{args.name}' -> {path}")
    print("Edit that file to make it yours, then:")
    print(f"  doxa init --lens-template {args.name}")
    return 0


def cmd_lenses_remove(args: argparse.Namespace) -> int:
    path = remove_user_lens(args.name)
    print(f"Removed user lens '{args.name}' ({path}).")
    return 0


def cmd_lenses_path(args: argparse.Namespace) -> int:
    print(user_lens_dir())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doxa",
        description="Build and query a verbatim-grounded belief base -- every answer cites a real quote.",
        epilog=(
            "quickstart:\n"
            "  doxa demo                   try it on bundled public-domain data\n"
            "  doxa init                   create your own base (writes doxa.yaml)\n"
            "  doxa ingest <file|url|->    mine a source into beliefs + quotes\n"
            '  doxa query "<question>"     ask -- answers cite verbatim quotes\n'
            "\n"
            "  doxa guide                  full walkthrough for humans\n"
            "  doxa status                 where things stand\n"
            "  doxa skill install --harness claude-code   drive doxa from an AI agent\n"
            "\n"
            "run `doxa` with no command for a quick start, or `doxa <command> -h` for details."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=False, metavar="<command>")

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
    init.add_argument("--lens-template", help="Seed the lens from a built-in or user template (see `doxa lenses list`).")
    init.add_argument("--full", action="store_true", help="Write the full documented config instead of the compact starter config.")
    init.set_defaults(func=cmd_init)

    ingest = subparsers.add_parser("ingest", help="Ingest one or more sources (text, PDF, URL, YouTube, or '-' from stdin).")
    ingest.add_argument("source", nargs="+", help="One or more files/URLs (shell globs work), or '-' for stdin.")
    ingest.add_argument("--config")
    ingest.add_argument("--reingest", action="store_true", help="Replace a source already in the base instead of skipping it.")
    ingest.add_argument("--title", help="Override title metadata for the ingested source.")
    ingest.add_argument("--author", help="Override author metadata for the ingested source.")
    ingest.add_argument("--url", help="Attach source URL metadata for the ingested source.")
    ingest.add_argument(
        "--via",
        choices=available_fetchers(),
        help="Override the URL fetcher (requests, jina, firecrawl, brightdata, command, or a browsing agent: claude/codex/hermes).",
    )
    ingest.add_argument(
        "--mode",
        choices=INGEST_MODES,
        help="How an agent/command fetcher scrapes: markdown (default), browser (render JS), or extract (with --prompt).",
    )
    ingest.add_argument(
        "--prompt",
        help="Fetch/extract instruction for agent (claude/codex/hermes) or command fetchers, e.g. 'extract product name, price, reviews as JSON'.",
    )
    ingest.add_argument(
        "--yolo",
        action="store_true",
        help="Run agent/command fetchers unattended: codex --dangerously-bypass-approvals, hermes --yolo, command shell. Trusted sources only.",
    )
    ingest.set_defaults(func=cmd_ingest)

    index = subparsers.add_parser("index", help="Build optional Postgres/pgvector semantic index.")
    index.add_argument("--config")
    index.set_defaults(func=cmd_index)

    query = subparsers.add_parser("query", help="Query beliefs and linked verbatim quotes.")
    query.add_argument("query")
    query.add_argument("--config")
    query.add_argument("--search", choices=["keyword", "semantic", "hybrid"], default="keyword")
    query.add_argument("--limit", "--top", dest="limit", type=int, default=5)
    query.add_argument("--domain", action="append", default=[], help="Boost results tagged with domain:<slug>. Repeatable.")
    query.add_argument("--domains", default="", help="Comma-separated domain slugs to boost.")
    query.add_argument("--no-domain-boost", action="store_true", help="Disable configured domain preference boosts.")
    query.add_argument("--answer", action="store_true", help="Format results as a clean evidence brief (claim + grounding quotes).")
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

    banner = subparsers.add_parser("banner", help="Print the bundled doxa terminal banner.")
    banner.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Control ANSI color output. auto colors only when stdout is a TTY.",
    )
    banner.add_argument("--no-color", action="store_const", dest="color", const="never", help="Alias for --color never.")
    banner.add_argument("--ansi", action="store_const", dest="color", const="always", help="Alias for --color always.")
    banner.set_defaults(func=cmd_banner)

    guide = subparsers.add_parser("guide", help="Print a guided walkthrough (for humans new to doxa).")
    guide.set_defaults(func=cmd_guide)

    status = subparsers.add_parser("status", help="Show config, data location, and belief/quote counts.")
    status.add_argument("--config")
    status.set_defaults(func=cmd_status)

    doctor = subparsers.add_parser("doctor", help="Check config, storage, provider, and semantic-index readiness.")
    doctor.add_argument("--config")
    doctor.set_defaults(func=cmd_doctor)

    sources_p = subparsers.add_parser("sources", help="List or remove ingested sources.")
    sources_p.add_argument("--config")
    sources_p.set_defaults(func=cmd_sources)
    sources_sub = sources_p.add_subparsers(dest="sources_command")
    s_list = sources_sub.add_parser("list", help="List ingested sources with belief/quote counts.")
    s_list.add_argument("--config", default=argparse.SUPPRESS)
    s_list.set_defaults(func=cmd_sources)
    s_rm = sources_sub.add_parser("remove", help="Remove a source and its beliefs/quotes by id.")
    s_rm.add_argument("id")
    s_rm.add_argument("--config", default=argparse.SUPPRESS)
    s_rm.set_defaults(func=cmd_sources)

    domains = subparsers.add_parser("domains", help="View or edit domain retrieval preferences.")
    domains.add_argument("--config")
    domains.set_defaults(func=cmd_domains)
    domain_sub = domains.add_subparsers(dest="domain_command")
    view = domain_sub.add_parser("view", help="Show the terminal domain-weight chart.")
    view.add_argument("--config", default=argparse.SUPPRESS)
    view.set_defaults(func=cmd_domains)
    set_parser = domain_sub.add_parser("set", help="Set a domain weight from 0 to 10.")
    set_parser.add_argument("slug")
    set_parser.add_argument("weight", type=int)
    set_parser.add_argument("--config", default=argparse.SUPPRESS)
    set_parser.set_defaults(func=cmd_domains)
    add = domain_sub.add_parser("add", help="Add a new domain weight.")
    add.add_argument("slug")
    add.add_argument("weight", nargs="?", type=int, default=6)
    add.add_argument("--config", default=argparse.SUPPRESS)
    add.set_defaults(func=cmd_domains)
    remove = domain_sub.add_parser("remove", help="Remove a domain weight.")
    remove.add_argument("slug")
    remove.add_argument("--config", default=argparse.SUPPRESS)
    remove.set_defaults(func=cmd_domains)
    reset = domain_sub.add_parser("reset", help="Reset domain weights to doxa defaults.")
    reset.add_argument("--config", default=argparse.SUPPRESS)
    reset.set_defaults(func=cmd_domains)
    export = domain_sub.add_parser("export", help="Export domain weights as YAML or JSON.")
    export.add_argument("--config", default=argparse.SUPPRESS)
    export.add_argument("--json", action="store_true")
    export.set_defaults(func=cmd_domains)
    edit = domain_sub.add_parser("edit", help="Edit domain weights in $VISUAL or $EDITOR.")
    edit.add_argument("--config", default=argparse.SUPPRESS)
    edit.set_defaults(func=cmd_domains)

    skill = subparsers.add_parser("skill", help="Install or inspect the portable agent skill.")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    install = skill_sub.add_parser("install", help="Install skill/SKILL.md into an agent harness.")
    install.add_argument("--harness", default="generic", help="claude-code, codex, hermes, openclaw, generic, or a custom label with --dest")
    install.add_argument("--scope", choices=["user", "project"], default="user")
    install.add_argument("--dest")
    install.set_defaults(func=cmd_skill_install)

    lenses = subparsers.add_parser("lenses", help="Browse and manage lens templates (the library of starting lenses).")
    lenses_sub = lenses.add_subparsers(dest="lenses_command", required=True)
    l_list = lenses_sub.add_parser("list", help="List built-in and user lens templates.")
    l_list.set_defaults(func=cmd_lenses_list)
    l_show = lenses_sub.add_parser("show", help="Show a lens template as a copy-pasteable lens: block.")
    l_show.add_argument("name")
    l_show.set_defaults(func=cmd_lenses_show)
    l_add = lenses_sub.add_parser("add", help="Save a user lens template (fork a built-in or supply your own).")
    l_add.add_argument("name")
    l_add.add_argument("--from", dest="from_template", help="Fork an existing template by name.")
    l_add.add_argument("--file", help="Load the lens from a YAML file.")
    l_add.add_argument("--summary", help="One-line summary for `doxa lenses list`.")
    l_add.add_argument("--description", help="Lens description (what to mine).")
    l_add.add_argument("--question", help="Guiding question for the lens.")
    l_add.set_defaults(func=cmd_lenses_add)
    l_remove = lenses_sub.add_parser("remove", help="Remove a user lens template.")
    l_remove.add_argument("name")
    l_remove.set_defaults(func=cmd_lenses_remove)
    l_path = lenses_sub.add_parser("path", help="Print the user lens directory.")
    l_path.set_defaults(func=cmd_lenses_path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        # No subcommand: greet with the banner + a curated "start here" landing.
        sys.stdout.write(render_banner(color="auto", stream=sys.stdout))
        sys.stdout.write("\n\n")
        sys.stdout.write(overview_text(color=_stdout_color()))
        sys.stdout.write("\n")
        return 0
    try:
        return int(args.func(args))
    except DoxaError as exc:
        return _print_error(exc)
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("\naborted.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - last resort: friendly error, never a raw traceback
        if os.environ.get("DOXA_DEBUG"):
            raise
        return _print_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
