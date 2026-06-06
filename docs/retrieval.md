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

Tokens are lowercased, stopword-filtered, and Porter-stemmed, so morphological
variants match: `factions` finds `faction`, `conform` finds `conformity`.
Stemming is symmetric across documents and the query and never alters stored
text (the verbatim guarantee is untouched). Disable it with `retrieval.stem: false`.

A multi-word query that appears as an exact contiguous phrase in a belief or
quote gets an extra precision boost (`retrieval.phrase_boost`), ranking true
phrase matches above scattered-term matches.

The default terminal view is the raw retrieval record format. Add `--answer`
when you want a deterministic local answer for a human reader:

```bash
doxa query "self-reliance" --search keyword --answer
```

Answer rendering uses only returned, quote-backed beliefs. It may clean
non-quote prose, but it prints quote strings exactly as stored. JSON output
remains the raw retrieval payload.

Useful config:

```yaml
retrieval:
  stem: true            # Porter stemming + stopword removal for keyword search
  candidate_limit: 50
  quote_boost: 2.0      # how strongly a matching quote lifts its belief
  phrase_boost: 0.5     # extra weight when the exact query phrase appears in a doc
  max_quotes_per_result: 2
```

`candidate_limit` overfetches before final ranking. `quote_boost` controls how
strongly quote hits lift the linked belief. `phrase_boost` rewards exact
contiguous phrase matches. `max_quotes_per_result` defaults to `2` for scannable
output (set `null` to keep every linked quote); direct quote hits are ordered
first.

Semantic retrieval needs embeddings and Postgres/pgvector:

```bash
python -m pip install -e ".[embeddings,postgres]"
export DOXA_POSTGRES_DSN=postgresql://...
doxa index
doxa query "political conflict" --search semantic
```

Queries are embedded with the model's query instruction (e.g. bge-v1.5's
retrieval prefix) while documents are embedded plain -- the standard asymmetric
setup for short-query to long-passage retrieval. No extra config is needed, and
existing indexes stay valid (only the query side changed).

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
uses active aliases as a conservative candidate-discovery leg after the literal
query has matched at least one document; configure this with
`retrieval.domain_query_boost` or set it to `0` for literal keyword-only
candidate selection.

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
