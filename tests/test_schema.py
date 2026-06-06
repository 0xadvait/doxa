from __future__ import annotations

import pytest

from doxa.schema import Belief, DoxaError, quote_is_verbatim


def test_quote_is_verbatim_normalizes_whitespace() -> None:
    source = "Trust thyself:\n  every heart vibrates to that iron string."
    assert quote_is_verbatim("Trust thyself: every heart vibrates to that iron string.", source)


def test_belief_requires_core_fields() -> None:
    with pytest.raises(DoxaError):
        Belief.from_dict({"id": "b1", "belief": "Missing fields"})


def test_belief_round_trip() -> None:
    belief = Belief.from_dict(
        {
            "id": "b1",
            "belief": "A worthy life requires examination.",
            "reasoning": "The quote states this directly.",
            "stance": "supports",
            "conviction": 0.96,
            "tags": ["examination"],
            "source": {"title": "Apology", "author": "Plato", "date": "1892", "url": ""},
        }
    )
    assert belief.to_dict()["source"]["title"] == "Apology"
    assert belief.conviction == 0.96


def test_belief_accepts_legacy_conviction_labels() -> None:
    belief = Belief.from_dict(
        {
            "id": "b1",
            "belief": "Legacy local stores may use label convictions.",
            "reasoning": "Older doxa data used strings such as strong/exploring.",
            "stance": "endorses",
            "conviction": "strong",
        }
    )
    assert belief.conviction == 0.85

