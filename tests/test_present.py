from __future__ import annotations

from argparse import Namespace
import json

import pytest

from doxa.cli import _resolve_presentation, build_parser
from doxa.present import (
    DEFAULT_PROFILE,
    HAWKING_PROFILE,
    PLAIN_PROFILE,
    Move,
    PresentationProfile,
    available_profiles,
    get_profile,
    render_directive,
)
from doxa.schema import DoxaError


def test_default_profile_is_plain_and_listed_first() -> None:
    assert DEFAULT_PROFILE == "plain"
    assert available_profiles()[0] == "plain"
    assert set(available_profiles()) == {"plain", "hawking"}


def test_plain_profile_emits_no_directive() -> None:
    assert PLAIN_PROFILE.is_plain()
    assert PLAIN_PROFILE.render_directive() == ""
    assert render_directive(None) == ""
    assert render_directive("plain") == ""


def test_get_profile_is_case_insensitive_and_defaults() -> None:
    assert get_profile(None).name == "plain"
    assert get_profile("HAWKING").name == "hawking"
    assert get_profile("  hawking  ").name == "hawking"


def test_unknown_profile_raises_doxa_error() -> None:
    with pytest.raises(DoxaError):
        get_profile("bogus")


def test_hawking_profile_is_complete_and_grounded() -> None:
    assert not HAWKING_PROFILE.is_plain()
    assert len(HAWKING_PROFILE.moves) == 8
    # every move carries a short verbatim exemplar so the agent can pattern-match
    assert all(move.exemplar for move in HAWKING_PROFILE.moves)
    assert HAWKING_PROFILE.arc and HAWKING_PROFILE.constraints and HAWKING_PROFILE.avoid


def test_hawking_directive_carries_structure_and_grounding() -> None:
    directive = HAWKING_PROFILE.render_directive()
    assert "=== doxa presentation directive: hawking ===" in directive
    assert "=== end presentation directive ===" in directive
    # the inviolable grounding rule must survive into the emitted directive
    assert "never the evidence" in directive
    assert "invent nothing" in directive
    # arc, a signature move, and a verbatim exemplar with attribution
    assert "procession of minds" in directive
    assert "In other words, the universe is expanding." in directive
    assert "A Brief History of Time" in directive


def test_directive_is_deterministic() -> None:
    assert HAWKING_PROFILE.render_directive() == HAWKING_PROFILE.render_directive()


def test_to_dict_includes_rendered_directive_and_attributed_moves() -> None:
    data = HAWKING_PROFILE.to_dict()
    assert data["name"] == "hawking"
    assert data["directive"] == HAWKING_PROFILE.render_directive()
    assert len(data["moves"]) == 8
    assert all(move["exemplar_source"] for move in data["moves"])


def test_profile_without_moves_is_treated_as_plain() -> None:
    profile = PresentationProfile(name="bare", title="Bare", summary="s")
    assert profile.is_plain()
    assert profile.render_directive() == ""

    with_move = PresentationProfile(
        name="voiced",
        title="Voiced",
        summary="s",
        moves=(Move(name="m", directive="d", exemplar="e"),),
    )
    assert not with_move.is_plain()
    assert "voiced" in with_move.render_directive()


def test_resolve_presentation_flag_overrides_config_default() -> None:
    config = {"presentation": {"default": "hawking"}}
    assert _resolve_presentation(Namespace(present="plain"), config).name == "plain"
    assert _resolve_presentation(Namespace(present=None), config).name == "hawking"
    # absent config key falls back to plain
    assert _resolve_presentation(Namespace(present=None), {}).name == "plain"


# --- CLI integration: runs against the bundled public-domain demo data ---


def _run(argv: list[str], capsys) -> tuple[int, str]:
    args = build_parser().parse_args(argv)
    code = int(args.func(args))
    return code, capsys.readouterr().out


def test_query_plain_emits_no_directive(capsys) -> None:
    code, out = _run(["query", "self-reliance", "--top", "1"], capsys)
    assert code == 0
    assert "presentation directive" not in out
    assert "1." in out


def test_query_hawking_prepends_directive_then_evidence(capsys) -> None:
    code, out = _run(["query", "self-reliance", "--top", "1", "--present", "hawking"], capsys)
    assert code == 0
    assert "=== doxa presentation directive: hawking ===" in out
    # the directive comes before the first retrieved result
    assert out.index("presentation directive") < out.index("1.")
    # evidence is still present and unchanged in form
    assert "quote=" in out


def test_query_json_plain_stays_a_bare_list(capsys) -> None:
    code, out = _run(["query", "self-reliance", "--top", "1", "--json"], capsys)
    assert code == 0
    assert isinstance(json.loads(out), list)


def test_query_json_hawking_wraps_results_with_presentation(capsys) -> None:
    code, out = _run(
        ["query", "self-reliance", "--top", "1", "--present", "hawking", "--json"], capsys
    )
    assert code == 0
    payload = json.loads(out)
    assert set(payload) == {"presentation", "results"}
    assert payload["presentation"]["name"] == "hawking"
    assert isinstance(payload["results"], list)


def test_present_subcommand_lists_and_prints_directive(capsys) -> None:
    code, out = _run(["present", "--list"], capsys)
    assert code == 0
    assert "plain" in out and "hawking" in out

    code, out = _run(["present", "hawking"], capsys)
    assert code == 0
    assert "presentation directive: hawking" in out

    code, out = _run(["present", "plain"], capsys)
    assert code == 0
    assert "plain:" in out  # plain has no directive, prints its summary line


def test_present_flag_parses_choices() -> None:
    assert build_parser().parse_args(["query", "x", "--present", "hawking"]).present == "hawking"
    assert build_parser().parse_args(["query", "x"]).present is None
