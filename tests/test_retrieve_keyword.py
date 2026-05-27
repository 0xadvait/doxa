from __future__ import annotations

from doxa.config import load_config
from doxa.retrieve import search


def test_keyword_search_returns_belief_with_verbatim_quotes() -> None:
    config = load_config(None)
    results, warnings = search("self-reliance conformity", config, search_type="keyword", limit=3)
    assert warnings == []
    assert results
    assert any(result.belief.id == "b_emerson_nonconformity" for result in results)
    for result in results:
        assert result.quotes
        assert all(quote.quote for quote in result.quotes)

