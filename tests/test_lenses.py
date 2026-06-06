"""Tests for the lens library: built-in templates, init --lens-template, user lenses."""
from __future__ import annotations

import pytest

from doxa.cli import main
from doxa.config import load_config
from doxa.lens import normalize_lens
from doxa.lenses import (
    builtin_lens_names,
    get_lens_template,
    lens_catalog,
    save_user_lens,
    template_to_config_lens,
    user_lens_names,
)
from doxa.schema import DoxaError

EXPECTED = {
    "durable-beliefs",
    "founder-strategy",
    "investment-memo",
    "technical-design",
    "research-literature",
    "policy-analysis",
    "personal-principles",
    "customer-discovery",
}


def test_all_builtin_lenses_present_and_valid() -> None:
    names = set(builtin_lens_names())
    assert EXPECTED <= names, EXPECTED - names
    for name in names:
        template = get_lens_template(name)
        assert template.get("summary"), name
        lens = template_to_config_lens(template)
        # reduces to a real config lens the miner can consume
        normalized = normalize_lens(lens)
        assert normalized["name"] and normalized["description"] and normalized["question"], name
        assert isinstance(normalized["stances"], list) and normalized["stances"], name
        assert isinstance(normalized["tags"], list), name
        assert "summary" not in lens  # library-only metadata is stripped from the config block


def test_get_lens_template_unknown_raises() -> None:
    with pytest.raises(DoxaError):
        get_lens_template("does-not-exist")


def test_init_seeds_lens_from_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--provider", "codex-cli", "--lens-template", "founder-strategy"]) == 0
    config = load_config(tmp_path / "doxa.yaml", allow_demo_default=False)
    template = get_lens_template("founder-strategy")
    assert config["lens"]["name"] == "founder-strategy"
    assert config["lens"]["stances"] == template["stances"]
    assert config["lens"]["tags"] == template["tags"]
    assert config["lens"]["description"] == template["description"]


def test_init_lens_template_unknown_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--provider", "codex-cli", "--lens-template", "nope"]) != 0
    assert not (tmp_path / "doxa.yaml").exists()  # nothing written on a bad template


def test_lenses_list_and_show_output(capsys) -> None:
    assert main(["lenses", "list"]) == 0
    listed = capsys.readouterr().out
    for name in EXPECTED:
        assert name in listed
    assert main(["lenses", "show", "investment-memo"]) == 0
    shown = capsys.readouterr().out
    assert "lens:" in shown and "investment-memo" in shown and "bear-case" in shown


def test_user_lens_appears_and_shadows_builtin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOXA_LENS_DIR", str(tmp_path))
    # a brand-new user lens shows up in the catalog
    save_user_lens("my-thesis", {"summary": "mine", "description": "d", "question": "q?", "tags": ["t"]})
    assert "my-thesis" in user_lens_names()
    assert any(r["name"] == "my-thesis" and r["origin"] == "user" for r in lens_catalog())
    # a user lens with a built-in's name shadows the built-in
    save_user_lens("founder-strategy", {"summary": "custom", "description": "custom desc", "question": "q?"})
    assert get_lens_template("founder-strategy")["description"] == "custom desc"
    assert any(r["name"] == "founder-strategy" and r["origin"] == "user" for r in lens_catalog())


def test_lenses_add_fork_remove_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOXA_LENS_DIR", str(tmp_path))
    assert main(["lenses", "add", "team-strategy", "--from", "founder-strategy"]) == 0
    forked = get_lens_template("team-strategy")
    assert forked["stances"] == get_lens_template("founder-strategy")["stances"]
    assert (tmp_path / "team-strategy.yaml").exists()
    # and it's usable as an init template
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--yes", "--provider", "codex-cli", "--lens-template", "team-strategy"]) == 0
    assert main(["lenses", "remove", "team-strategy"]) == 0
    assert not (tmp_path / "team-strategy.yaml").exists()


def test_lenses_add_requires_description(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOXA_LENS_DIR", str(tmp_path))
    assert main(["lenses", "add", "empty"]) != 0  # no --from/--file/--description
