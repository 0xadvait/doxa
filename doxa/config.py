"""Configuration loading for doxa."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .schema import DoxaError


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_CONFIG_FILENAMES = ("doxa.yaml", "doxa.yml")


DEFAULT_CONFIG: dict[str, Any] = {
    "project": {"name": "doxa"},
    "data": {
        "dir": "data",
        "beliefs": "beliefs.jsonl",
        "quotes": "quotes.jsonl",
        "sources": "sources.jsonl",
    },
    "lens": {
        "name": "beliefs",
        "description": "Extract claims, stances, and reasons the source explicitly supports.",
        "question": "What durable beliefs does this source express?",
        "stances": ["supports", "questions", "rejects", "complicates"],
        "tags": [],
    },
    "llm": {
        "provider": "codex-cli",
        "model": "",
        "temperature": 0,
    },
    "providers": {
        "codex-cli": {
            "binary": "codex",
            "flags": ["exec", "--dangerously-bypass-approvals-and-sandbox"],
            "output_flag": "-o",
        },
        "claude-cli": {
            "binary": "claude",
            "flags": ["-p", "{prompt}", "--output-format", "json"],
        },
        "openai": {
            "base_url": "",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4.1-mini",
        },
        "openai-compatible": {
            "base_url": "",
            "api_key_env": "OPENAI_API_KEY",
            "model": "",
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "model": "claude-3-5-sonnet-latest",
        },
    },
    "sources": {
        "fetcher": "requests",
        "brightdata": {
            "api_token_env": "BRIGHTDATA_API_TOKEN",
            "zone_env": "BRIGHTDATA_ZONE",
        },
    },
    "retrieval": {
        "default_search": "keyword",
        "limit": 5,
        "candidate_limit": 50,
        "quote_boost": 2.0,
        "max_quotes_per_result": None,
        "bm25_k1": 1.5,
        "bm25_b": 0.75,
        "rrf_k": 60,
    },
    "preferences": {
        "domains": {
            "general": 2,
            "research": 3,
            "technical": 3,
            "policy": 2,
            "creative": 2,
        },
    },
    "embeddings": {
        "model": "BAAI/bge-small-en-v1.5",
        "dimension": 384,
    },
    "postgres": {
        "dsn_env": "DOXA_POSTGRES_DSN",
        "table_prefix": "doxa",
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries without mutating either input."""

    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_config_path(start: Path | None = None) -> Path | None:
    """Find a doxa config in the given directory."""

    root = start or Path.cwd()
    for filename in DEFAULT_CONFIG_FILENAMES:
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - pyyaml is a core dependency
        raise DoxaError("Missing dependency: install pyyaml or reinstall doxa with core dependencies.") from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise DoxaError(f"Config file must contain a YAML mapping: {path}")
    return data


def load_config(path: str | Path | None = None, *, allow_demo_default: bool = True) -> dict[str, Any]:
    """Load config, falling back to bundled demo data when no config exists."""

    config_path = Path(path).expanduser().resolve() if path else find_config_path()
    config = deepcopy(DEFAULT_CONFIG)
    if config_path:
        config = deep_merge(config, load_yaml(config_path))
        config["_config_path"] = str(config_path)
        config["_base_dir"] = str(config_path.parent)
    else:
        config["_config_path"] = ""
        config["_base_dir"] = str(Path.cwd())
        if allow_demo_default:
            from .resources import demo_data_dir

            config["data"]["dir"] = str(demo_data_dir())
    return config


def data_dir(config: dict[str, Any]) -> Path:
    """Return the configured data directory as an absolute path."""

    configured = Path(str(config.get("data", {}).get("dir", "data"))).expanduser()
    if configured.is_absolute():
        return configured
    return Path(str(config.get("_base_dir") or Path.cwd())) / configured


def data_file(config: dict[str, Any], key: str) -> Path:
    """Return a configured JSONL data file path."""

    name = str(config.get("data", {}).get(key, f"{key}.jsonl"))
    return data_dir(config) / name
