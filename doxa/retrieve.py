"""Keyword, semantic, and hybrid retrieval."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
import re
from typing import Any

from .domains import active_domain_weights, domain_aliases, domain_multiplier_for_result
from .embed import embed_query, embed_texts
from .schema import Belief, DoxaError, Quote, RetrievalResult
from .stem import STOPWORDS, stem as _stem
from .store import JsonlStore, postgres_connect


TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


@dataclass(slots=True)
class _SearchDoc:
    kind: str
    belief_id: str
    text: str
    quote: Quote | None = None


def tokenize(text: str, *, stem: bool = True) -> list[str]:
    """Lowercase tokens; optionally drop stopwords and Porter-stem.

    Stemming is symmetric (same for documents and queries), so variants like
    ``factions``/``faction`` match. Stored data is never touched -- this only
    shapes the in-memory BM25 index and the query.
    """
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    if not stem:
        return tokens
    filtered = [t for t in tokens if t not in STOPWORDS]
    if not filtered:  # a query made only of stopwords -> keep the raw tokens
        filtered = tokens
    return [_stem(t) for t in filtered]


def belief_document_text(belief: Belief) -> str:
    return "\n".join(
        [
            belief.belief,
            belief.reasoning,
            belief.stance,
            " ".join(belief.tags),
            belief.source.title,
            belief.source.author,
        ]
    )


def quote_document_text(quote: Quote) -> str:
    return "\n".join(
        [
            quote.quote,
            quote.context,
            quote.speaker,
            " ".join(quote.tags),
            quote.source.title,
            quote.source.author,
        ]
    )


def document_text(result: RetrievalResult) -> str:
    quote_text = "\n".join(quote.quote + "\n" + quote.context for quote in result.quotes)
    return "\n".join(
        [
            result.belief.belief,
            result.belief.reasoning,
            result.belief.stance,
            " ".join(result.belief.tags),
            result.belief.source.title,
            result.belief.source.author,
            quote_text,
        ]
    )


def _bm25_scores(query_terms: list[str], docs: list[list[str]], *, k1: float, b: float) -> list[tuple[int, float]]:
    if not docs:
        return []
    doc_freq: Counter[str] = Counter()
    for doc in docs:
        doc_freq.update(set(doc))
    avgdl = sum(len(doc) for doc in docs) / max(len(docs), 1)
    scores: list[tuple[int, float]] = []
    for index, doc in enumerate(docs):
        term_freq = Counter(doc)
        score = 0.0
        dl = len(doc) or 1
        for term in query_terms:
            if term_freq[term] == 0:
                continue
            idf = math.log(1 + (len(docs) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            numerator = term_freq[term] * (k1 + 1)
            denominator = term_freq[term] + k1 * (1 - b + b * dl / avgdl)
            score += idf * numerator / denominator
        if score > 0:
            scores.append((index, score))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def _linked_quotes(quotes: list[Quote]) -> dict[str, list[Quote]]:
    by_belief: dict[str, list[Quote]] = {}
    for quote in quotes:
        for belief_id in quote.belief_ids:
            by_belief.setdefault(belief_id, []).append(quote)
    return by_belief


def _cap_quotes(quotes: list[Quote], max_quotes_per_result: int | None) -> list[Quote]:
    if max_quotes_per_result is None:
        return quotes
    return quotes[: max(max_quotes_per_result, 0)]


def _merge_quotes(first: list[Quote], second: list[Quote], max_quotes_per_result: int | None = None) -> list[Quote]:
    merged: list[Quote] = []
    seen: set[str] = set()
    for quote in [*first, *second]:
        if quote.id in seen:
            continue
        seen.add(quote.id)
        merged.append(quote)
    return _cap_quotes(merged, max_quotes_per_result)


def _rank_results(
    results: list[RetrievalResult],
    config: dict[str, Any],
    *,
    limit: int,
    max_quotes_per_result: int | None,
    domains: list[str] | None = None,
    domain_boost: bool = True,
) -> list[RetrievalResult]:
    active_weights = active_domain_weights(config, domains, enabled=domain_boost)
    aliases = domain_aliases(config) if active_weights else {}
    boosted: list[tuple[int, RetrievalResult]] = []
    for order, result in enumerate(results):
        quotes = _cap_quotes(result.quotes, max_quotes_per_result)
        multiplier = domain_multiplier_for_result(result.belief, result.quotes, active_weights, aliases)
        boosted.append(
            (
                order,
                RetrievalResult(belief=result.belief, quotes=quotes, score=result.score * multiplier),
            )
        )
    boosted.sort(key=lambda item: (-item[1].score, item[0]))
    return [result for _, result in boosted[:limit]]


def _domain_query_terms(config: dict[str, Any], domains: list[str] | None, *, enabled: bool, stem: bool = True) -> list[str]:
    active_weights = active_domain_weights(config, domains, enabled=enabled)
    if not active_weights:
        return []
    aliases = domain_aliases(config)
    terms: list[str] = []
    seen: set[str] = set()
    for slug in active_weights:
        for value in aliases.get(slug, [slug]):
            for term in tokenize(value, stem=stem):
                if term in seen:
                    continue
                seen.add(term)
                terms.append(term)
    return terms


def keyword_search(
    query: str,
    store: JsonlStore,
    *,
    limit: int = 5,
    candidate_limit: int | None = None,
    quote_boost: float = 2.0,
    max_quotes_per_result: int | None = None,
    k1: float = 1.5,
    b: float = 0.75,
    domains: list[str] | None = None,
    domain_boost: bool = True,
    rank_domain_boost: bool | None = None,
) -> list[RetrievalResult]:
    """Pure-Python BM25 over separate belief docs and quote docs."""

    beliefs = store.beliefs()
    quotes = store.quotes()
    if not beliefs:
        return []
    by_belief = {belief.id: belief for belief in beliefs}
    quote_by_id = {quote.id: quote for quote in quotes}
    linked_quotes = _linked_quotes(quotes)
    docs: list[_SearchDoc] = []
    for belief in beliefs:
        docs.append(_SearchDoc(kind="belief", belief_id=belief.id, text=belief_document_text(belief)))
    for quote in quotes:
        docs.append(_SearchDoc(kind="quote", belief_id="", text=quote_document_text(quote), quote=quote))
    stem_tokens = bool(store.config.get("retrieval", {}).get("stem", True))
    query_terms = tokenize(query, stem=stem_tokens)
    if not query_terms:
        return []
    candidate_limit = max(candidate_limit or limit, limit)
    doc_terms = [tokenize(doc.text, stem=stem_tokens) for doc in docs]
    literal_doc_scores = _bm25_scores(query_terms, doc_terms, k1=k1, b=b)
    if not literal_doc_scores:
        return []
    combined_doc_scores: Counter[int] = Counter()
    for doc_index, raw_score in literal_doc_scores:
        combined_doc_scores[doc_index] += raw_score
    # Precision: reward docs that contain the exact contiguous query phrase, so a
    # multi-word query ranks true phrase matches above scattered-term matches.
    # Matched on raw (unstemmed) text so stemming can't blur the phrase.
    phrase_boost = max(float(store.config.get("retrieval", {}).get("phrase_boost", 0.5)), 0.0)
    if phrase_boost > 0 and len(query_terms) >= 2:
        phrase = " ".join(tokenize(query, stem=False))
        if phrase:
            for doc_index, raw_score in literal_doc_scores:
                if phrase in " ".join(tokenize(docs[doc_index].text, stem=False)):
                    combined_doc_scores[doc_index] += raw_score * phrase_boost
    domain_query_boost = max(float(store.config.get("retrieval", {}).get("domain_query_boost", 0.25)), 0.0)
    if domain_boost and domain_query_boost > 0:
        for doc_index, raw_score in _bm25_scores(
            _domain_query_terms(store.config, domains, enabled=True, stem=stem_tokens),
            doc_terms,
            k1=k1,
            b=b,
        ):
            combined_doc_scores[doc_index] += raw_score * domain_query_boost
    doc_scores = sorted(combined_doc_scores.items(), key=lambda item: (-item[1], item[0]))
    belief_scores: Counter[str] = Counter()
    matched_quote_scores: dict[str, Counter[str]] = {}
    for doc_index, raw_score in doc_scores:
        doc = docs[doc_index]
        if doc.kind == "belief":
            belief_scores[doc.belief_id] += raw_score
            continue
        if doc.quote is None:
            continue
        quote_score = raw_score * quote_boost
        for belief_id in doc.quote.belief_ids:
            if belief_id not in by_belief:
                continue
            belief_scores[belief_id] += quote_score
            matched_quote_scores.setdefault(belief_id, Counter())[doc.quote.id] += quote_score
    if not belief_scores:
        return []
    if rank_domain_boost is None:
        rank_domain_boost = domain_boost
    belief_order = {belief.id: index for index, belief in enumerate(beliefs)}
    quote_order = {quote.id: index for index, quote in enumerate(quotes)}
    grouped: list[RetrievalResult] = []
    for belief_id, score in belief_scores.items():
        matched = matched_quote_scores.get(belief_id, Counter())
        matched_quotes = sorted(
            (quote_by_id[quote_id] for quote_id in matched if quote_id in quote_by_id),
            key=lambda quote: (-matched[quote.id], quote_order.get(quote.id, 0)),
        )
        matched_ids = {quote.id for quote in matched_quotes}
        remaining_quotes = [quote for quote in linked_quotes.get(belief_id, []) if quote.id not in matched_ids]
        ordered_quotes = [*matched_quotes, *remaining_quotes]
        grouped.append(RetrievalResult(belief=by_belief[belief_id], quotes=ordered_quotes, score=float(score)))
    grouped.sort(key=lambda result: (-result.score, belief_order.get(result.belief.id, 0)))
    candidates = grouped[:candidate_limit]
    return _rank_results(
        candidates,
        store.config,
        limit=limit,
        max_quotes_per_result=max_quotes_per_result,
        domains=domains,
        domain_boost=rank_domain_boost,
    )


def semantic_search(
    query: str,
    config: dict[str, Any],
    *,
    limit: int = 5,
    candidate_limit: int | None = None,
    max_quotes_per_result: int | None = None,
    domains: list[str] | None = None,
    domain_boost: bool = True,
) -> list[RetrievalResult]:
    """Search a pgvector index with cosine distance."""

    candidate_limit = max(candidate_limit or limit, limit)
    vector = embed_query(query, config)
    prefix = str(config.get("postgres", {}).get("table_prefix", "doxa"))
    conn = postgres_connect(config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT payload, 1 - (embedding <=> %s::vector) AS score
                FROM {prefix}_beliefs
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vector, vector, candidate_limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    store = JsonlStore(config)
    by_id = {belief.id: belief for belief in store.beliefs()}
    scored: list[tuple[Belief, float]] = []
    for payload, score in rows:
        raw = payload if isinstance(payload, dict) else json.loads(payload)
        belief = by_id.get(str(raw.get("id"))) or Belief.from_dict(raw)
        scored.append((belief, float(score)))
    return _rank_results(
        store.linked_results(scored),
        config,
        limit=limit,
        max_quotes_per_result=max_quotes_per_result,
        domains=domains,
        domain_boost=domain_boost,
    )


def reciprocal_rank_fusion(
    rankings: list[list[RetrievalResult]],
    *,
    k: int = 60,
    limit: int = 5,
    max_quotes_per_result: int | None = None,
) -> list[RetrievalResult]:
    by_id: dict[str, RetrievalResult] = {}
    scores: Counter[str] = Counter()
    for ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            if result.belief.id in by_id:
                existing = by_id[result.belief.id]
                by_id[result.belief.id] = RetrievalResult(
                    belief=existing.belief,
                    quotes=_merge_quotes(existing.quotes, result.quotes, max_quotes_per_result),
                    score=existing.score,
                )
            else:
                by_id[result.belief.id] = result
            scores[result.belief.id] += 1 / (k + rank)
    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        RetrievalResult(
            belief=by_id[belief_id].belief,
            quotes=_cap_quotes(by_id[belief_id].quotes, max_quotes_per_result),
            score=float(score),
        )
        for belief_id, score in fused[:limit]
    ]


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _max_quotes(value: Any) -> int | None:
    if value is None:
        return None
    return max(_int_or_default(value, 0), 0)


def search(
    query: str,
    config: dict[str, Any],
    *,
    search_type: str = "keyword",
    limit: int = 5,
    domains: list[str] | None = None,
    domain_boost: bool = True,
) -> tuple[list[RetrievalResult], list[str]]:
    """Run retrieval and return results plus non-fatal warnings."""

    store = JsonlStore(config)
    retrieval = config.get("retrieval", {})
    search_type = search_type or str(retrieval.get("default_search", "keyword"))
    candidate_limit = max(_int_or_default(retrieval.get("candidate_limit"), max(limit * 3, limit)), limit)
    max_quotes_per_result = _max_quotes(retrieval.get("max_quotes_per_result"))
    quote_boost = float(retrieval.get("quote_boost", 2.0))
    if search_type == "keyword":
        return keyword_search(
            query,
            store,
            limit=limit,
            candidate_limit=candidate_limit,
            quote_boost=quote_boost,
            max_quotes_per_result=max_quotes_per_result,
            k1=float(retrieval.get("bm25_k1", 1.5)),
            b=float(retrieval.get("bm25_b", 0.75)),
            domains=domains,
            domain_boost=domain_boost,
        ), []
    if search_type == "semantic":
        return semantic_search(
            query,
            config,
            limit=limit,
            candidate_limit=candidate_limit,
            max_quotes_per_result=max_quotes_per_result,
            domains=domains,
            domain_boost=domain_boost,
        ), []
    if search_type == "hybrid":
        keyword = keyword_search(
            query,
            store,
            limit=candidate_limit,
            candidate_limit=candidate_limit,
            quote_boost=quote_boost,
            max_quotes_per_result=max_quotes_per_result,
            domains=domains,
            domain_boost=domain_boost,
            rank_domain_boost=False,
        )
        warnings: list[str] = []
        try:
            semantic = semantic_search(
                query,
                config,
                limit=candidate_limit,
                candidate_limit=candidate_limit,
                max_quotes_per_result=max_quotes_per_result,
                domain_boost=False,
            )
            rankings = [keyword, semantic]
        except DoxaError as exc:
            warnings.append(
                f"Semantic leg unavailable; hybrid fell back to keyword only: {exc} "
                "(run `doxa index` with DOXA_POSTGRES_DSN set to enable semantic/hybrid)."
            )
            rankings = [keyword]
        fused = reciprocal_rank_fusion(
            rankings,
            k=int(retrieval.get("rrf_k", 60)),
            limit=candidate_limit,
            max_quotes_per_result=max_quotes_per_result,
        )
        return _rank_results(
            fused,
            config,
            limit=limit,
            max_quotes_per_result=max_quotes_per_result,
            domains=domains,
            domain_boost=domain_boost,
        ), warnings
    raise DoxaError(f"Unknown search type '{search_type}'. Use keyword, semantic, or hybrid.")
