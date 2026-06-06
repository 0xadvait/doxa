# Retrieval

Keyword retrieval is pure Python BM25:

```bash
doxa query "self-reliance" --search keyword
```

Keyword search indexes two in-memory document types:

- belief docs: belief text, reasoning, stance, tags, and source metadata
- quote docs: verbatim quote, context, speaker, tags, and source metadata

Quote doc hits are grouped back to their linked beliefs. This means a rare
phrase that appears only inside a quote can still retrieve the belief grounded
by that quote. When a quote matched the query, it is displayed before other
linked quotes.

Useful config:

```yaml
retrieval:
  candidate_limit: 50
  quote_boost: 2.0
  max_quotes_per_result: null
```

`candidate_limit` overfetches before final ranking. `quote_boost` controls how
strongly quote hits affect the linked belief score. Set `max_quotes_per_result`
to an integer for compact output; the default `null` preserves all linked quotes,
with direct quote hits ordered first.

Semantic retrieval needs embeddings and Postgres/pgvector:

```bash
python -m pip install -e ".[embeddings,postgres]"
export DOXA_POSTGRES_DSN=postgresql://...
doxa index
doxa query "political conflict" --search semantic
```

Hybrid retrieval uses reciprocal rank fusion with `k=60` by default. It combines
keyword and semantic rankings when both are available. If semantic search is not
configured, `doxa query --search hybrid` falls back to keyword and prints a
warning.

## Domains

Domain preferences are small 0-10 weights under `preferences.domains`. Mining
prompts ask the provider to tag clear matches as `domain:<slug>` on beliefs and
quotes. Retrieval then gives matching tags a small boost after overfetching.
It also checks `preferences.domain_aliases` so active domains can match older
plain tags. For example, `crypto` can match `token-economics`, `startups` can
match `founders`, and `relationships` can match `trust`. Keyword search also
uses active aliases as a conservative candidate-discovery leg before slicing;
configure this with `retrieval.domain_query_boost` or set it to `0` for literal
keyword-only candidate selection.

View or edit preferences:

```bash
doxa domains
doxa domains set technical 8
doxa domains export
```

Focus a query on one or more domains:

```bash
doxa query "incident response tradeoffs" --domain technical
doxa query "market structure and incentives" --domains finance,policy
doxa query "plain keyword behavior" --no-domain-boost
```
