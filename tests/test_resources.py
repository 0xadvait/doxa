from __future__ import annotations

from pathlib import Path

from doxa.config import load_config
from doxa.resources import banner_text, demo_config_path, demo_data_dir, skill_text


def test_bundled_demo_resources_are_loadable() -> None:
    config_path = demo_config_path()
    data_dir = demo_data_dir()

    assert config_path.name == "doxa.yaml"
    assert data_dir.joinpath("beliefs.jsonl").exists()
    assert load_config(config_path, allow_demo_default=False)["data"]["dir"] == "data"


def test_bundled_skill_resource_is_loadable() -> None:
    text = skill_text()
    assert "doxa Skill" in text
    assert "No quote" in text


def test_bundled_banner_resource_is_loadable() -> None:
    text = banner_text()
    lines = text.splitlines()

    assert "DOXA // BELIEF ORACLE" in text
    assert "NO QUOTE // NO CLAIM" in text
    assert all(len(line) < 100 for line in lines)


def test_readme_svg_banner_exists_and_is_github_safe() -> None:
    svg_path = Path(__file__).resolve().parents[1] / "assets" / "banner.svg"
    assert svg_path.exists()

    svg = svg_path.read_text(encoding="utf-8")
    assert svg.startswith("<svg ")
    assert "NO QUOTE // NO CLAIM" in svg
    assert "<script" not in svg.lower()
    assert Path.home().as_posix() not in svg
