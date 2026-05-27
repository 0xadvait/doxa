"""Keyword, semantic, and hybrid retrieval."""

from __future__ import annotations

from collections import Counter
import json
import math
import re
from typing import Any

from .embed import embed_texts
from .schema import Belief, DoxaError, RetrievalResult
from .store import JsonlStore, postgres_connect


TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


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


def keyword_search(query: str, store: JsonlStore, *, limit: int = 5, k1: float = 1.5, b: float = 0.75) -> list[RetrievalResult]:
    """Pure-Python BM25 over beliefs plus linked quotes."""

    all_results = store.linked_results([(belief, 0.0) for belief in store.beliefs()])
    if not all_results:
        return []
    docs = [tokenize(document_text(result)) for result in all_results]
    query_terms = tokenize(query)
    if not query_terms:
        return []
    doc_freq: Counter[str] = Counter()
    for doc in docs:
        doc_freq.update(set(doc))
    avgdl = sum(len(doc) for doc in docs) / max(len(docs), 1)
    scores: list[tuple[RetrievalResult, float]] = []
    for result, doc in zip(all_results, docs):
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
            scores.append((result, score))
    scores.sort(key=lambda item: item[1], reverse=True)
    return [
        RetrievalResult(belief=result.belief, quotes=result.quotes, score=score)
        for result, score in scores[:limit]
    ]


def semantic_search(query: str, config: dict[str, Any], *, limit: int = 5) -> list[RetrievalResult]:
    """Search a pgvector index with cosine distance."""

    vector = embed_texts([query], config)[0]
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
                (vector, vector, limit),
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
    return store.linked_results(scored)


def reciprocal_rank_fusion(rankings: list[list[RetrievalResult]], *, k: int = 60, limit: int = 5) -> list[RetrievalResult]:
    by_id: dict[str, RetrievalResult] = {}
    scores: Counter[str] = Counter()
    for ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            by_id[result.belief.id] = result
            scores[result.belief.id] += 1 / (k + rank)
    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        RetrievalResult(belief=by_id[belief_id].belief, quotes=by_id[belief_id].quotes, score=float(score))
        for belief_id, score in fused[:limit]
    ]


def search(query: str, config: dict[str, Any], *, search_type: str = "keyword", limit: int = 5) -> tuple[list[RetrievalResult], list[str]]:
    """Run retrieval and return results plus non-fatal warnings."""

    store = JsonlStore(config)
    retrieval = config.get("retrieval", {})
    search_type = search_type or str(retrieval.get("default_search", "keyword"))
    if search_type == "keyword":
        return keyword_search(
            query,
            store,
            limit=limit,
            k1=float(retrieval.get("bm25_k1", 1.5)),
            b=float(retrieval.get("bm25_b", 0.75)),
        ), []
    if search_type == "semantic":
        return semantic_search(query, config, limit=limit), []
    if search_type == "hybrid":
        keyword = keyword_search(query, store, limit=max(limit * 3, limit))
        warnings: list[str] = []
        try:
            semantic = semantic_search(query, config, limit=max(limit * 3, limit))
            rankings = [keyword, semantic]
        except DoxaError as exc:
            warnings.append(f"Semantic leg unavailable; hybrid fell back to keyword only: {exc}")
            rankings = [keyword]
        return reciprocal_rank_fusion(rankings, k=int(retrieval.get("rrf_k", 60)), limit=limit), warnings
    raise DoxaError(f"Unknown search type '{search_type}'. Use keyword, semantic, or hybrid.")

