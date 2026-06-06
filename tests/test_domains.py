from __future__ import annotations

import pytest

from doxa.domains import chart, export_domain_weights, normalize_weight, parse_domain_selectors
from doxa.schema import DoxaError


def test_parse_domain_selectors_dedupes_and_normalizes() -> None:
    assert parse_domain_selectors(["Technical Systems"], "policy,technical-systems") == [
        "technical-systems",
        "policy",
    ]


def test_chart_renders_terminal_bars() -> None:
    rendered = chart({"technical": 8})
    assert "technical" in rendered
    assert "[████████░░]" in rendered
    assert "8/10" in rendered


def test_export_domain_weights_can_emit_yaml() -> None:
    exported = export_domain_weights({"technical": 8})
    assert "preferences:" in exported
    assert "technical: 8" in exported


def test_domain_weight_validation() -> None:
    with pytest.raises(DoxaError):
        normalize_weight(11)
