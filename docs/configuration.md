# Configuration

Run `doxa init` to create `doxa.yaml`. Paths in the config are relative to the
config file.

Important sections:

- `data`: JSONL paths for beliefs, quotes, and source records.
- `lens`: the extraction objective, allowed stances, and suggested tags.
- `llm`: selected provider and model.
- `providers`: provider-specific binary paths, flags, API key env vars, and base URLs.
- `sources`: URL fetcher settings. `requests` is the default; `brightdata`
  routes URL ingestion through BrightData Web Unlocker using env vars.
- `retrieval`: keyword and hybrid search parameters.
- `preferences`: user preference weights, including retrieval/mining domains.
- `postgres`: DSN env var and table prefix for semantic search.

Core commands work with no API key. Ingestion needs a configured provider.
Agents should start with the repo-root [AGENTS.md](../AGENTS.md); the portable
skill is [skill/SKILL.md](../skill/SKILL.md).

Example source fetcher config:

```yaml
sources:
  fetcher: requests
  brightdata:
    api_token_env: BRIGHTDATA_API_TOKEN
    zone_env: BRIGHTDATA_ZONE
```

Use `doxa ingest - --title "Title"` for stdin text, including content fetched by
an agent's BrightData MCP. Use `doxa ingest <url> --via brightdata` for direct
BrightData CLI fetching.

Retrieval defaults:

```yaml
retrieval:
  default_search: keyword
  limit: 5
  candidate_limit: 50
  quote_boost: 2.0
  domain_query_boost: 0.25
  max_quotes_per_result: null
  bm25_k1: 1.5
  bm25_b: 0.75
  rrf_k: 60
```

`candidate_limit` overfetches unique beliefs before final ranking. `quote_boost`
helps a rare phrase in a quote surface the linked belief. `domain_query_boost`
adds a small active-domain alias leg after the literal query has matched at
least one document, so legacy plain tags can supplement candidate discovery
without creating pure domain-only matches; set it to `0` for literal
keyword-only candidate selection. `max_quotes_per_result` can cap linked quotes
when you want compact output; leave it `null` to preserve every linked quote in
text and JSON output.

Domain preferences:

```yaml
preferences:
  domains:
    general: 2
    research: 3
    technical: 3
    policy: 2
    creative: 2
  domain_aliases:
    crypto: [token-economics, tokenomics, tokens, web3, blockchain, defi]
    startups: [startup, startups, founders, company-building]
    relationships: [trust, communication, friendship]
```

Weights are integers from 0 to 10. Mining prompts see these as `domain:<slug>`
tagging hints. Retrieval gives a small boost to beliefs or quotes with matching
domain tags, and the keyword retriever can use active aliases as a low-weight
candidate-discovery leg. Alias terms extend the exact `domain:<slug>` match for
retrieval, so older stores with plain tags such as `token-economics`,
`founders`, `trust`, `taste`, or `health` do not need a JSONL migration.

Manage domains from the CLI:

```bash
doxa domains
doxa domains set technical 8
doxa domains add finance 6
doxa domains remove creative
doxa domains reset
doxa domains export
```

All domain subcommands accept `--config`.
