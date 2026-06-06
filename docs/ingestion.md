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

## Web fetchers (pluggable)

doxa is not tied to one scraper. The URL fetcher is chosen per ingest with
`--via`, or set as a default with `sources.fetcher`. Built-ins:

- `requests` -- plain HTTP + stdlib HTML extraction (default, no key).
- `jina` -- Jina Reader, clean markdown, free (`JINA_API_KEY` optional for higher limits).
- `firecrawl` -- Firecrawl scrape API (`FIRECRAWL_API_KEY`).
- `brightdata` -- BrightData Web Unlocker (`BRIGHTDATA_API_TOKEN` + `BRIGHTDATA_ZONE`).
- `command` -- run any external tool or MCP bridge that prints text to stdout.
- `claude` / `codex` / `hermes` -- delegate the fetch to a coding agent's browsing
  (returns markdown; needs that CLI on PATH; invocation overridable under `sources.<agent>`).

Choose how an agent (or `command`) fetcher scrapes with `--mode` and `--prompt`:

```bash
doxa ingest <url> --via hermes                  # clean markdown (default)
doxa ingest <url> --via hermes --mode browser   # render JS / scroll, then markdown
doxa ingest <url> --via hermes --mode extract --prompt "name, price, rating as JSON"
doxa ingest <url> --via claude --prompt "return only the methods section"
```

`--prompt` is free-form: the agent uses whatever it has (SERP search, browser
automation, structured extraction, platform endpoints) to satisfy it. These flags
are ignored by the fixed-format fetchers (`requests`/`jina`/`firecrawl`/`brightdata`).

```bash
doxa ingest https://target.example --via jina
doxa ingest https://target.example --via firecrawl
doxa ingest https://target.example --via brightdata
```

```yaml
sources:
  fetcher: jina            # default URL fetcher
  jina: { api_key_env: JINA_API_KEY }
  firecrawl: { api_key_env: FIRECRAWL_API_KEY }
  brightdata: { api_token_env: BRIGHTDATA_API_TOKEN, zone_env: BRIGHTDATA_ZONE }
```

The `command` fetcher is the universal hook -- wire any scraper or MCP. It runs
your command (with `{url}` substituted) and ingests its stdout:

```yaml
sources:
  fetcher: command
  command:
    argv: ["my-fetch", "{url}"]   # or shell: "my-fetch {url}"; prints text to stdout
```

MCP-equipped agents can also skip fetchers and pipe pre-fetched markdown straight
into `doxa ingest -`. Add a custom fetcher in Python with
`doxa.sources.fetchers.register_fetcher(name, fn)`.

The miner asks the configured provider for JSON with `beliefs` and `quotes`.
Every returned quote is checked against the source text. Quotes that fail the
verbatim check are dropped before storage, and beliefs with no surviving quote
link are dropped as unanchored.
