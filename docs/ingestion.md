# Ingestion

```bash
doxa ingest ./source.txt
doxa ingest ./paper.pdf
doxa ingest https://example.com/essay
doxa ingest https://www.youtube.com/watch?v=...
printf 'Trust thyself: every heart vibrates to that iron string.' | \
  doxa ingest - --title "Self-Reliance excerpt" --author "Ralph Waldo Emerson"
```

Text and default URL ingestion use the standard library. PDF ingestion requires
`doxa[pdf]`. YouTube ingestion requires `doxa[youtube]`. Use `doxa ingest -`
to read source text from stdin; `--title`, `--author`, and `--url` attach
metadata to stdin or text sources.

## Tough sources / BrightData

For an MCP-equipped agent, the easiest path is to fetch a bot-protected source
with the harness's BrightData MCP and pipe the returned markdown or text into
doxa. This path does not require a BrightData token in doxa:

```bash
printf '%s' "$FETCHED_MARKDOWN" | \
  doxa ingest - --title "Article title" --url "https://target.example"
```

For direct CLI use, doxa can route URL fetching through BrightData Web Unlocker:

```bash
export BRIGHTDATA_API_TOKEN=...
export BRIGHTDATA_ZONE=...
doxa ingest https://target.example --via brightdata
```

Config defaults:

```yaml
sources:
  fetcher: requests
  brightdata:
    api_token_env: BRIGHTDATA_API_TOKEN
    zone_env: BRIGHTDATA_ZONE
```

Set `sources.fetcher: brightdata` to make BrightData the default URL fetcher.

The miner asks the configured provider for JSON with `beliefs` and `quotes`.
Every returned quote is checked against the source text. Quotes that fail the
verbatim check are dropped before storage, and beliefs with no surviving quote
link are dropped as unanchored.
