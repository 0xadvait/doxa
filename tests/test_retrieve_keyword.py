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


def test_keyword_search_does_not_return_domain_only_no_match(tmp_path: Path) -> None:
    source = _source()
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b_domain",
                "belief": "Operational runbooks should be maintained with technical precision.",
                "reasoning": "The domain tag should not make this a match by itself.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": ["domain:technical"],
                "source": source,
            }
        ],
        quotes=[
            {
                "id": "q_domain",
                "quote": "Precise runbooks reduce operational ambiguity.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": ["domain:technical"],
                "belief_ids": ["b_domain"],
            }
        ],
    )

    results, warnings = search("zephyrless arglebargle", config, search_type="keyword", limit=3, domains=["technical"])

    assert warnings == []
    assert results == []


def test_keyword_candidate_limit_counts_unique_beliefs_after_quote_grouping(tmp_path: Path) -> None:
    source = _source()
    many_quotes = [
        {
            "id": f"q_many_{index}",
            "quote": "monopoly needle phrase",
            "speaker": "",
            "source": source,
            "context": "",
            "tags": [],
            "belief_ids": ["b_many"],
        }
        for index in range(60)
    ]
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b_many",
                "belief": "One belief has many matching quote documents.",
                "reasoning": "It should rank first without crowding out every other belief candidate.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
            {
                "id": "b_two",
                "belief": "A second belief also has a matching quote.",
                "reasoning": "It should remain eligible after quote document grouping.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
            {
                "id": "b_three",
                "belief": "A third belief also has a matching quote.",
                "reasoning": "It should remain eligible after quote document grouping.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
        ],
        quotes=[
            *many_quotes,
            {
                "id": "q_two",
                "quote": "monopoly needle phrase",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b_two"],
            },
            {
                "id": "q_three",
                "quote": "monopoly needle phrase",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b_three"],
            },
        ],
    )
    config["retrieval"]["max_quotes_per_result"] = 3

    results, warnings = search("monopoly needle phrase", config, search_type="keyword", limit=3)

    assert warnings == []
    assert [result.belief.id for result in results] == ["b_many", "b_two", "b_three"]
    assert [quote.id for quote in results[0].quotes] == ["q_many_0", "q_many_1", "q_many_2"]
    assert [quote.id for quote in results[1].quotes] == ["q_two"]
    assert [quote.id for quote in results[2].quotes] == ["q_three"]


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


def test_domain_boost_can_promote_default_legacy_alias_tag(tmp_path: Path) -> None:
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
                "id": "b_legacy",
                "belief": "Shared retrieval phrase supports the same surface match.",
                "reasoning": "The score should tie before domain preferences.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": ["token-economics"],
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
                "id": "q_legacy",
                "quote": "Shared retrieval phrase.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": ["token-economics"],
                "belief_ids": ["b_legacy"],
            },
        ],
    )
    config["preferences"]["domains"]["crypto"] = 10

    unboosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
        domain_boost=False,
    )
    boosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
    )

    assert unboosted[0].belief.id == "b_plain"
    assert boosted[0].belief.id == "b_legacy"


def test_domain_boost_can_promote_custom_legacy_alias_tag(tmp_path: Path) -> None:
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
                "id": "b_custom",
                "belief": "Shared retrieval phrase supports the same surface match.",
                "reasoning": "The score should tie before domain preferences.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": ["boardroom"],
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
                "id": "q_custom",
                "quote": "Shared retrieval phrase.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": ["boardroom"],
                "belief_ids": ["b_custom"],
            },
        ],
    )
    config["preferences"]["domain_aliases"]["operator"] = ["boardroom"]

    unboosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
        domains=["operator"],
        domain_boost=False,
    )
    boosted, _ = search(
        "shared retrieval phrase",
        config,
        search_type="keyword",
        limit=2,
        domains=["operator"],
    )

    assert unboosted[0].belief.id == "b_plain"
    assert boosted[0].belief.id == "b_custom"


def test_domain_alias_query_boost_can_discover_legacy_tagged_candidate(tmp_path: Path) -> None:
    source = _source()
    config = _write_store(
        tmp_path,
        beliefs=[
            {
                "id": "b_literal",
                "belief": "Celadon planning is a generic builder workflow.",
                "reasoning": "This is the only belief with the literal query term.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": [],
                "source": source,
            },
            {
                "id": "b_legacy",
                "belief": "Clinical milestones should be sequenced by evidence windows.",
                "reasoning": "The legacy plain tag should participate in candidate discovery.",
                "stance": "supports",
                "conviction": 0.8,
                "tags": ["health"],
                "source": source,
            },
        ],
        quotes=[
            {
                "id": "q_literal",
                "quote": "A generic planning quote supports the literal result.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": [],
                "belief_ids": ["b_literal"],
            },
            {
                "id": "q_legacy",
                "quote": "A clinical milestone quote supports the legacy-tagged result.",
                "speaker": "",
                "source": source,
                "context": "",
                "tags": ["health"],
                "belief_ids": ["b_legacy"],
            },
        ],
    )
    config["retrieval"]["candidate_limit"] = 2

    unboosted, _ = search(
        "celadon",
        config,
        search_type="keyword",
        limit=2,
        domains=["biotech"],
        domain_boost=False,
    )
    disabled = deepcopy(config)
    disabled["retrieval"]["domain_query_boost"] = 0
    zero_boost, _ = search(
        "celadon",
        disabled,
        search_type="keyword",
        limit=2,
        domains=["biotech"],
    )
    boosted, _ = search(
        "celadon",
        config,
        search_type="keyword",
        limit=2,
        domains=["biotech"],
    )

    assert [result.belief.id for result in unboosted] == ["b_literal"]
    assert [result.belief.id for result in zero_boost] == ["b_literal"]
    assert "b_legacy" in [result.belief.id for result in boosted]
