from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from doxa.config import DEFAULT_CONFIG
from doxa.config import load_config
from doxa.retrieve import search
from doxa.store import write_jsonl


def _source(title: str = "Test Source") -> dict[str, str]:
    return {"title": title, "author": "Tester", "date": "2026", "url": ""}


def _temp_config(tmp_path: Path) -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    config["_base_dir"] = str(tmp_path)
    config["_config_path"] = ""
    config["data"]["dir"] = "."
    config["retrieval"]["candidate_limit"] = 20
    config["retrieval"]["quote_boost"] = 2.0
    config["retrieval"]["max_quotes_per_result"] = 1
    return config


def _write_store(tmp_path: Path, beliefs: list[dict], quotes: list[dict]) -> dict:
    config = _temp_config(tmp_path)
    write_jsonl(tmp_path / "beliefs.jsonl", beliefs)
    write_jsonl(tmp_path / "quotes.jsonl", quotes)
    write_jsonl(tmp_path / "sources.jsonl", [])
    return config


def test_keyword_search_returns_belief_with_verbatim_quotes() -> None:
    config = load_config(None)
    results, warnings = search("self-reliance conformity", config, search_type="keyword", limit=3)
    assert warnings == []
    assert results
    assert any(result.belief.id == "b_emerson_nonconformity" for result in results)
    for result in results:
        assert result.quotes
        assert all(quote.quote for quote in result.quotes)


def test_keyword_search_recalls_phrase_that_only_appears_in_quote(tmp_path: Path) -> None:
    source = _source()
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b1",
                "belief": "A practical rule can be hidden in supporting evidence.",
                "reasoning": "The belief text intentionally omits the rare phrase.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
            {
                "id": "b2",
                "belief": "Another ordinary claim sits nearby.",
                "reasoning": "It does not share the rare phrase.",
                "stance": "supports",
                "conviction": 0.7,
                "tags": [],
                "source": source,
            },
        ],
        quotes=[
            {
                "id": "q_unmatched",
                "quote": "This first quote supports the same belief without unusual terms.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b1"],
            },
            {
                "id": "q_match",
                "quote": "The lapis heliotrope axiom appears only inside this quotation.",
                "speaker": "",
                "source": source,
                "context": "A rare phrase appears in evidence, not the distilled belief.",
                "tags": [],
                "belief_ids": ["b1"],
            },
            {
                "id": "q_other",
                "quote": "A separate quote grounds a separate belief.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b2"],
            },
        ],
    )

    results, warnings = search("lapis heliotrope axiom", config, search_type="keyword", limit=3)

    assert warnings == []
    assert results[0].belief.id == "b1"
    assert [quote.id for quote in results[0].quotes] == ["q_match"]


def test_keyword_search_preserves_all_linked_quotes_when_uncapped(tmp_path: Path) -> None:
    source = _source()
    quotes = [
        {
            "id": f"q{i}",
            "quote": f"Shared audit phrase quote {i}.",
            "speaker": "",
            "source": source,
            "context": "",
            "tags": [],
            "belief_ids": ["b1"],
        }
        for i in range(5)
    ]
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b1",
                "belief": "Shared audit phrase should keep all evidence links by default.",
                "reasoning": "JSON/API consumers need complete quote lists unless configured otherwise.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            }
        ],
        quotes=quotes,
    )
    config["retrieval"]["max_quotes_per_result"] = None

    results, _ = search("shared audit phrase", config, search_type="keyword", limit=1)

    assert [quote.id for quote in results[0].quotes] == ["q0", "q1", "q2", "q3", "q4"]


def test_domain_boost_can_promote_matching_domain_tag(tmp_path: Path) -> None:
    source = _source()
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b_plain",
                "belief": "Shared retrieval phrase supports the same surface match.",
                "reasoning": "The score should tie before domain preferences.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
            {
                "id": "b_domain",
                "belief": "Shared retrieval phrase supports the same surface match.",
                "reasoning": "The score should tie before domain preferences.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": ["domain:technical"],
                "source": source,
            },
        ],
        quotes=[
            {
                "id": "q_plain",
                "quote": "Shared retrieval phrase.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b_plain"],
            },
            {
                "id": "q_domain",
                "quote": "Shared retrieval phrase.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": ["domain:technical"],
                "belief_ids": ["b_domain"],
            },
        ],
    )
    config["preferences"]["domains"]["technical"] = 10

    unboosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
        domains=["technical"],
        domain_boost=False,
    )
    boosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
        domains=["technical"],
    )

    assert unboosted[0].belief.id == "b_plain"
    assert boosted[0].belief.id == "b_domain"
