"""Discoverability: the landing, the guide, and the agent skill surface the toolbox."""
from __future__ import annotations

from doxa.guide import guide_text, overview_text
from doxa.resources import skill_text


def test_overview_points_beyond_the_basics() -> None:
    out = overview_text()
    assert "lenses list" in out
    assert "doxa guide" in out


def test_guide_surfaces_the_full_toolbox() -> None:
    g = guide_text()
    for keyword in ["lenses list", "--lens-template", "--via", "--search hybrid", "doxa eval", "doxa doctor"]:
        assert keyword in g, keyword


def test_skill_teaches_the_full_surface_to_agents() -> None:
    s = skill_text().lower()
    for keyword in ["lenses list", "--lens-template", "doxa eval", "doxa doctor", "--via", "no quote, no claim"]:
        assert keyword in s, keyword
