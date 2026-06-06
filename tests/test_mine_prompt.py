"""The miner extracts everything the lens surfaces -- no assumed belief/quote count."""
from __future__ import annotations

from doxa.lens import build_extraction_prompt


def test_extraction_prompt_mines_exhaustively_without_count_cap() -> None:
    config = {"lens": {"name": "t", "description": "d", "question": "q?", "stances": ["supports"], "tags": []}}
    _system, user = build_extraction_prompt(config, {"title": "T"}, "some source text")
    low = user.lower()
    assert "every distinct belief" in low
    assert "target number" in low
    assert "omit nothing" in low
    assert "never cap" in low
