"""The lens library -- built-in and user lens templates.

A lens is the question doxa asks while reading. "What lens should I use?" is the
first hard question a new user hits, so doxa ships an opinionated library you can
browse (`doxa lenses list/show`), seed a config from (`doxa init --lens-template
<name>`), and make your own (drop a YAML in the user lens dir, or `doxa lenses
add`). Built-in templates live as package data under ``_assets/lenses``; user
templates live under ``user_lens_dir()`` and shadow built-ins of the same name.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .resources import resource_ref
from .schema import DoxaError

_LENS_DIRNAME = "lenses"
# Fields that belong in a config `lens:` block (everything else, e.g. `summary`,
# is library-only metadata for listing).
_CONFIG_FIELDS = ("name", "description", "question", "stances", "tags")
_DEFAULT_STANCES = ["supports", "questions", "rejects", "complicates"]


def user_lens_dir() -> Path:
    """Where a user's own lens templates live (override with ``DOXA_LENS_DIR``)."""
    override = os.environ.get("DOXA_LENS_DIR")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "doxa" / "lenses"


def _load_yaml(text: str, where: str) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise DoxaError(f"lens template {where} must be a YAML mapping")
    return data


def builtin_lens_names() -> list[str]:
    try:
        root = resource_ref(_LENS_DIRNAME)
    except DoxaError:
        return []
    return sorted(c.name[:-5] for c in root.iterdir() if c.name.endswith(".yaml"))


def _load_builtin(name: str) -> dict[str, Any]:
    ref = resource_ref(_LENS_DIRNAME, f"{name}.yaml")
    return _load_yaml(ref.read_text(encoding="utf-8"), f"'{name}'")


def user_lens_names() -> list[str]:
    directory = user_lens_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def _load_user(name: str) -> dict[str, Any]:
    path = user_lens_dir() / f"{name}.yaml"
    if not path.is_file():
        raise DoxaError(f"user lens not found: {path}")
    return _load_yaml(path.read_text(encoding="utf-8"), str(path))


def lens_catalog() -> list[dict[str, str]]:
    """Every template as ``{name, summary, origin}`` for listing; user shadows builtin."""
    rows: dict[str, dict[str, str]] = {}
    for name in builtin_lens_names():
        rows[name] = {"name": name, "summary": str(_load_builtin(name).get("summary", "")), "origin": "builtin"}
    for name in user_lens_names():
        rows[name] = {"name": name, "summary": str(_load_user(name).get("summary", "")), "origin": "user"}
    return [rows[name] for name in sorted(rows)]


def get_lens_template(name: str) -> dict[str, Any]:
    """Full template dict by name. User templates shadow built-ins of the same name."""
    if name in set(user_lens_names()):
        return _load_user(name)
    if name in set(builtin_lens_names()):
        return _load_builtin(name)
    available = ", ".join(row["name"] for row in lens_catalog()) or "(none)"
    raise DoxaError(f"unknown lens template '{name}'. Available: {available}")


def template_to_config_lens(template: dict[str, Any]) -> dict[str, Any]:
    """Reduce a template to the config `lens:` mapping (drops library-only fields)."""
    lens = {key: template[key] for key in _CONFIG_FIELDS if key in template}
    lens.setdefault("name", template.get("name", "beliefs"))
    lens.setdefault("stances", list(_DEFAULT_STANCES))
    lens.setdefault("tags", [])
    return lens


def save_user_lens(name: str, template: dict[str, Any]) -> Path:
    """Write a user lens template to ``user_lens_dir()`` and return its path."""
    import yaml

    directory = user_lens_dir()
    directory.mkdir(parents=True, exist_ok=True)
    ordered = {
        "name": name,
        "summary": str(template.get("summary", "")),
        "description": str(template.get("description", "")),
        "question": str(template.get("question", "")),
        "stances": template.get("stances") or list(_DEFAULT_STANCES),
        "tags": template.get("tags") or [],
    }
    path = directory / f"{name}.yaml"
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def remove_user_lens(name: str) -> Path:
    path = user_lens_dir() / f"{name}.yaml"
    if not path.is_file():
        raise DoxaError(f"no user lens named '{name}' at {path}")
    path.unlink()
    return path
