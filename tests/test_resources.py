from __future__ import annotations

from doxa.config import load_config
from doxa.resources import demo_config_path, demo_data_dir, skill_text


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
