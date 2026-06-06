"""Domain preference helpers for prompts, retrieval, and CLI config edits."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable

from .config import DEFAULT_CONFIG, find_config_path, load_yaml
from .schema import Belief, DoxaError, Quote


DOMAIN_TAG_PREFIX = "domain:"
DEFAULT_QUERY_DOMAIN_WEIGHT = 6
MAX_DOMAIN_WEIGHT = 10

DEFAULT_DOMAIN_WEIGHTS: dict[str, int] = {
    "general": 2,
    "research": 3,
    "technical": 3,
    "policy": 2,
    "creative": 2,
}


def normalize_domain_slug(raw: str) -> str:
    """Return a stable domain slug suitable for a ``domain:<slug>`` tag."""

    slug = re.sub(r"[\s_]+", "-", str(raw or "").strip().lower())
    slug = re.sub(r"[^a-z0-9-]+", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise DoxaError("Domain slug cannot be empty.")
    return slug


def normalize_weight(raw: Any) -> int:
    try:
        weight = int(raw)
    except (TypeError, ValueError) as exc:
        raise DoxaError(f"Domain weight must be an integer from 0 to {MAX_DOMAIN_WEIGHT}.") from exc
    if not 0 <= weight <= MAX_DOMAIN_WEIGHT:
        raise DoxaError(f"Domain weight must be between 0 and {MAX_DOMAIN_WEIGHT}.")
    return weight


def domain_tag(slug: str) -> str:
    return f"{DOMAIN_TAG_PREFIX}{normalize_domain_slug(slug)}"


def parse_domain_selectors(repeated: list[str] | None = None, comma_list: str | None = None) -> list[str]:
    """Parse repeated ``--domain`` and comma-separated ``--domains`` values."""

    seen: set[str] = set()
    parsed: list[str] = []
    values = list(repeated or [])
    if comma_list:
        values.extend(part for part in comma_list.split(","))
    for value in values:
        if not str(value).strip():
            continue
        slug = normalize_domain_slug(str(value))
        if slug not in seen:
            seen.add(slug)
            parsed.append(slug)
    return parsed


def domain_weights(config: dict[str, Any]) -> dict[str, int]:
    """Return configured domain weights, accepting older configs without preferences."""

    prefs = config.get("preferences") or {}
    if not isinstance(prefs, dict):
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    raw = prefs.get("domains", DEFAULT_DOMAIN_WEIGHTS)
    if not isinstance(raw, dict):
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    weights: dict[str, int] = {}
    for slug, weight in raw.items():
        weights[normalize_domain_slug(str(slug))] = normalize_weight(weight)
    return weights


def active_domain_weights(
    config: dict[str, Any],
    requested: list[str] | None = None,
    *,
    enabled: bool = True,
) -> dict[str, int]:
    """Return the domain weights that should affect retrieval for a query."""

    if not enabled:
        return {}
    configured = domain_weights(config)
    if requested:
        return {
            slug: configured.get(slug, DEFAULT_QUERY_DOMAIN_WEIGHT) or DEFAULT_QUERY_DOMAIN_WEIGHT
            for slug in parse_domain_selectors(requested)
        }
    return {slug: weight for slug, weight in configured.items() if weight > 0}


def domain_slugs_from_tags(tags: list[str]) -> set[str]:
    slugs: set[str] = set()
    for tag in tags:
        raw = str(tag).strip().lower()
        if raw.startswith(DOMAIN_TAG_PREFIX):
            try:
                slugs.add(normalize_domain_slug(raw[len(DOMAIN_TAG_PREFIX) :]))
            except DoxaError:
                continue
    return slugs


def domain_multiplier_for_tags(tags: list[str], active_weights: dict[str, int]) -> float:
    """Return a small multiplier based on matching domain tags."""

    if not active_weights:
        return 1.0
    matches = domain_slugs_from_tags(tags)
    if not matches:
        return 1.0
    weight = max((active_weights.get(slug, 0) for slug in matches), default=0)
    if weight <= 0:
        return 1.0
    return 1.0 + weight / 20.0


def domain_multiplier_for_result(belief: Belief, quotes: list[Quote], active_weights: dict[str, int]) -> float:
    tags = list(belief.tags)
    for quote in quotes:
        tags.extend(quote.tags)
    return domain_multiplier_for_tags(tags, active_weights)


def domain_prompt_lines(config: dict[str, Any]) -> list[str]:
    weights = domain_weights(config)
    enabled = [(slug, weight) for slug, weight in sorted(weights.items()) if weight > 0]
    if not enabled:
        return ["Domain preferences: none configured"]
    tags = ", ".join(f"domain:{slug}={weight}/10" for slug, weight in enabled)
    return [
        f"Domain preferences: {tags}",
        "When a source clearly fits one of these domains, add the matching domain:<slug> tag to both beliefs and quotes.",
    ]


def chart(weights: dict[str, int]) -> str:
    """Render a compact terminal chart for domain weights."""

    lines = ["doxa domain preferences", "weight 0-10; higher values boost matching domain:<slug> tags", ""]
    for slug, weight in sorted(weights.items()):
        bar = "█" * weight + "░" * (MAX_DOMAIN_WEIGHT - weight)
        lines.append(f"{slug:<16} [{bar}] {weight:>2}/{MAX_DOMAIN_WEIGHT}")
    if not weights:
        lines.append("(none configured)")
    return "\n".join(lines)


def resolve_config_write_path(path: str | Path | None = None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    found = find_config_path()
    return found.resolve() if found else (Path.cwd() / "doxa.yaml").resolve()


def _load_raw_config_for_write(path: Path) -> dict[str, Any]:
    if path.exists():
        return load_yaml(path)
    return {}


def write_raw_config(path: Path, config: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - pyyaml is a core dependency
        raise DoxaError("Missing dependency: install pyyaml or reinstall doxa with core dependencies.") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def update_domain_config(path: str | Path | None, updater: Callable[[dict[str, int]], dict[str, int]]) -> Path:
    """Update only ``preferences.domains`` in a YAML config file."""

    config_path = resolve_config_write_path(path)
    raw = _load_raw_config_for_write(config_path)
    prefs = raw.setdefault("preferences", {})
    if not isinstance(prefs, dict):
        raise DoxaError("Config preferences section must be a mapping.")
    current_raw = prefs.get("domains", DEFAULT_CONFIG.get("preferences", {}).get("domains", DEFAULT_DOMAIN_WEIGHTS))
    current = domain_weights({"preferences": {"domains": current_raw}})
    prefs["domains"] = updater(current)
    write_raw_config(config_path, raw)
    return config_path


def set_domain_weight(path: str | Path | None, slug: str, weight: Any) -> Path:
    normalized_slug = normalize_domain_slug(slug)
    normalized_weight = normalize_weight(weight)

    def updater(weights: dict[str, int]) -> dict[str, int]:
        updated = dict(weights)
        updated[normalized_slug] = normalized_weight
        return updated

    return update_domain_config(path, updater)


def add_domain_weight(path: str | Path | None, slug: str, weight: Any = DEFAULT_QUERY_DOMAIN_WEIGHT) -> Path:
    normalized_slug = normalize_domain_slug(slug)
    normalized_weight = normalize_weight(weight)

    def updater(weights: dict[str, int]) -> dict[str, int]:
        if normalized_slug in weights:
            raise DoxaError(f"Domain '{normalized_slug}' already exists. Use set to change it.")
        updated = dict(weights)
        updated[normalized_slug] = normalized_weight
        return updated

    return update_domain_config(path, updater)


def remove_domain_weight(path: str | Path | None, slug: str) -> Path:
    normalized_slug = normalize_domain_slug(slug)

    def updater(weights: dict[str, int]) -> dict[str, int]:
        updated = dict(weights)
        updated.pop(normalized_slug, None)
        return updated

    return update_domain_config(path, updater)


def reset_domain_weights(path: str | Path | None) -> Path:
    return update_domain_config(path, lambda _: dict(DEFAULT_DOMAIN_WEIGHTS))


def export_domain_weights(weights: dict[str, int], *, as_json: bool = False) -> str:
    if as_json:
        import json

        return json.dumps(weights, indent=2, sort_keys=True)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - pyyaml is a core dependency
        raise DoxaError("Missing dependency: install pyyaml or reinstall doxa with core dependencies.") from exc
    return yaml.safe_dump({"preferences": {"domains": weights}}, sort_keys=False).rstrip()


def edit_domain_weights(path: str | Path | None) -> Path:
    """Open domain weights in $VISUAL/$EDITOR and write the edited mapping."""

    config_path = resolve_config_write_path(path)
    raw = _load_raw_config_for_write(config_path)
    prefs = raw.get("preferences") or {}
    if not isinstance(prefs, dict):
        raise DoxaError("Config preferences section must be a mapping.")
    current_raw = prefs.get("domains", DEFAULT_DOMAIN_WEIGHTS)
    current = domain_weights({"preferences": {"domains": current_raw}})
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        raise DoxaError("Set VISUAL or EDITOR before using `doxa domains edit`, or use set/add/remove.")
    initial = export_domain_weights(current) + "\n"
    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", encoding="utf-8", delete=False) as handle:
        handle.write(initial)
        handle.flush()
        temp_path = Path(handle.name)
    try:
        proc = subprocess.run([editor, str(temp_path)], check=False)
        if proc.returncode != 0:
            raise DoxaError(f"Editor exited with status {proc.returncode}.")
        edited = load_yaml(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
    edited_domains = edited.get("preferences", {}).get("domains", edited.get("domains", edited))
    normalized = domain_weights({"preferences": {"domains": edited_domains}})

    def updater(_: dict[str, int]) -> dict[str, int]:
        return deepcopy(normalized)

    return update_domain_config(config_path, updater)
