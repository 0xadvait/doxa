from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from doxa.config import load_config
from doxa.store import JsonlStore, postgres_table_prefix

ROOT = Path(__file__).resolve().parents[1]
DANGEROUS_LITERALS = (
    "--dangerously-" + "bypass-approvals-and-sandbox",
    "--yolo",
)
UNSAFE_BOOL_KEYS = {"allow_shell", "unsafe_bypass", "unsafe_yolo"}


def example_yaml_paths() -> list[Path]:
    return [
        ROOT / "doxa.example.yaml",
        ROOT / "examples" / "demo" / "doxa.yaml",
        *sorted((ROOT / "examples" / "configs").glob("*.yaml")),
    ]


def walk_mapping(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from walk_mapping(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_mapping(child)


def test_example_yaml_files_parse_and_load() -> None:
    paths = example_yaml_paths()

    assert paths
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            parsed = yaml.safe_load(handle)
        assert isinstance(parsed, dict), path
        config = load_config(path, allow_demo_default=False)
        assert config["project"]["name"], path
        postgres_table_prefix(config)


def test_checked_in_examples_do_not_enable_unsafe_execution_defaults() -> None:
    for path in example_yaml_paths():
        text = path.read_text(encoding="utf-8")
        for needle in DANGEROUS_LITERALS:
            assert needle not in text, f"{path} contains {needle}"
        parsed = yaml.safe_load(text) or {}
        enabled = [key for key, value in walk_mapping(parsed) if key in UNSAFE_BOOL_KEYS and value is True]
        assert not enabled, f"{path} enables unsafe execution knobs: {enabled}"


def test_demo_example_store_is_valid() -> None:
    config = load_config(ROOT / "examples" / "demo" / "doxa.yaml", allow_demo_default=False)
    store = JsonlStore(config)

    assert len(store.sources()) == 3
    assert len(store.beliefs()) == 8
    assert len(store.quotes()) == 8
