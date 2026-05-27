"""Faithfulness and integrity checks for a doxa store."""

from __future__ import annotations

from typing import Any

from .schema import quote_is_verbatim
from .store import JsonlStore


def faithfulness_report(config: dict[str, Any]) -> dict[str, Any]:
    """Check quote verbatimness, link integrity, and orphan beliefs."""

    store = JsonlStore(config)
    beliefs = store.beliefs()
    quotes = store.quotes()
    sources = store.sources()
    belief_ids = {belief.id for belief in beliefs}

    source_text_by_title = {source.title: source.text for source in sources if source.text}
    invalid_quotes: list[dict[str, str]] = []
    checked_quotes = 0
    for quote in quotes:
        source_text = source_text_by_title.get(quote.source.title)
        if not source_text:
            continue
        checked_quotes += 1
        if not quote_is_verbatim(quote.quote, source_text):
            invalid_quotes.append({"id": quote.id, "quote": quote.quote, "source": quote.source.title})

    bad_links: list[dict[str, str]] = []
    linked_belief_ids: set[str] = set()
    for quote in quotes:
        for belief_id in quote.belief_ids:
            if belief_id not in belief_ids:
                bad_links.append({"quote_id": quote.id, "missing_belief_id": belief_id})
            else:
                linked_belief_ids.add(belief_id)
    orphan_beliefs = sorted(belief_ids - linked_belief_ids)
    quote_percent = 100.0
    if checked_quotes:
        quote_percent = round(100 * (checked_quotes - len(invalid_quotes)) / checked_quotes, 2)

    return {
        "beliefs": len(beliefs),
        "quotes": len(quotes),
        "sources": len(sources),
        "checked_quotes": checked_quotes,
        "quote_verbatim_percent": quote_percent,
        "invalid_quotes": invalid_quotes,
        "bad_links": bad_links,
        "orphan_beliefs": orphan_beliefs,
        "ok": not invalid_quotes and not bad_links and not orphan_beliefs,
    }

