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
