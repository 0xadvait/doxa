from __future__ import annotations

from doxa.lens import build_extraction_prompt, lens_text


def test_string_lens_is_treated_as_description() -> None:
    text = lens_text({"lens": "Extract beliefs about practical judgment."})
    assert "Lens name: beliefs" in text
    assert "Lens description: Extract beliefs about practical judgment." in text
    assert "Allowed stances: supports, questions, rejects, complicates" in text


def test_prompt_build_accepts_string_lens() -> None:
    _, user = build_extraction_prompt(
        {"lens": "Extract beliefs about courage."},
        {"title": "Example"},
        "Courage is steadiness under pressure.",
    )
    assert "Extract beliefs about courage." in user
    assert "Source text:" in user


def test_prompt_includes_domain_attention() -> None:
    _, user = build_extraction_prompt(
        {
            "lens": "Extract technical operating beliefs.",
            "preferences": {"domains": {"technical": 8, "policy": 0}},
        },
        {"title": "Example"},
        "Reliable systems need clear ownership.",
    )
    assert "Domain preferences: domain:technical=8/10" in user
    assert "domain:<slug>" in user
