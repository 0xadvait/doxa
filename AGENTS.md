# doxa Agent Guide

This guide is for an LLM agent that has landed in this repo and needs to help a
user set up or use doxa interactively. Be command-first and keep the user in the
loop for provider, model, and source choices.

## Detect

Run these from the repo root:

```bash
python --version
command -v doxa
doxa status   # config path, data dir, belief/quote counts, provider, semantic on/off
doxa demo     # smoke-test on bundled data, zero config
```

`doxa status` answers most "where do things stand" questions in one call. If it
reports `beliefs: 0`, the base is empty -- offer to `doxa ingest` a source rather
than querying. Re-run `doxa status` any time to recheck state.

If `doxa` is missing, install the local checkout:

```bash
python -m pip install -e ".[all]"
```

If the user wants smaller extras, install only what they need:

```bash
python -m pip install -e ".[pdf,youtube]"
python -m pip install -e ".[openai,anthropic]"
python -m pip install -e ".[embeddings,postgres]"
```

Check no-key mining CLIs:

```bash
command -v codex
command -v claude
```

Only if `doxa status` shows `semantic: off` and the user wants semantic/hybrid
search, set up Postgres + pgvector:

```bash
echo "$DOXA_POSTGRES_DSN"
psql "$DOXA_POSTGRES_DSN" -c "CREATE EXTENSION IF NOT EXISTS vector;"   # needs a superuser/owner role
doxa index
```

Otherwise use keyword search (the zero-setup default) until the user asks for
semantic or hybrid retrieval.

## Ask

Ask how the user wants to mine beliefs. This is the heart of setup.

- `codex-cli`: no API key; uses the existing Codex CLI auth.
- `claude-cli`: no API key; uses the existing Claude Code auth.
- `openai`: API key; default env var `OPENAI_API_KEY`.
- `openai-compatible` / Fireworks: custom or open-weights models; commonly
  `FIREWORKS_API_KEY` and a model like `accounts/fireworks/models/<slug>`.
- `anthropic`: API key; default env var `ANTHROPIC_API_KEY`.

Ask for the exact model when the provider needs one. If the user chooses an API
provider, help them set the key in their shell before ingestion:

```bash
export OPENAI_API_KEY=...
export FIREWORKS_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Configure

Prefer the interactive initializer:

```bash
doxa init
```

For scripts, write answers non-interactively:

```bash
doxa init ./doxa.yaml --yes --provider codex-cli
doxa init ./fireworks.yaml --yes --provider openai-compatible --model accounts/fireworks/models/<slug>
```

Help the user write a lens with three fields:

- `name`: short identifier.
- `description`: what kind of beliefs to extract.
- `question`: the guiding question doxa should ask of each source.

## First Source

Ask the user for the first trusted source, then ingest it:

```bash
doxa ingest <uri>
```

For pre-fetched text or copied notes, pipe stdin and attach metadata:

```bash
printf '%s' "$SOURCE_TEXT" | doxa ingest - --title "Title" --author "Author" --url "https://source.example"
```

Show the verbatim guarantee:

```bash
doxa eval
```

Query it (keyword is the zero-setup default):

```bash
doxa query "<user question>"
```

Use `--search hybrid` only after the user has built the optional Postgres/pgvector
index (`doxa index`); on a fresh base it just warns and falls back to keyword.

Review or undo what's been ingested with `doxa sources list` and
`doxa sources remove <id>`.

## Tough Sources / Web Fetchers

The URL fetcher is pluggable (`--via`, or `sources.fetcher` default):
`requests` (default), `jina` (free clean markdown), `firecrawl` (`FIRECRAWL_API_KEY`),
`brightdata` (`BRIGHTDATA_API_TOKEN` + `BRIGHTDATA_ZONE`), `command` (run any tool),
or a browsing agent -- `claude` / `codex` / `hermes` -- which fetches the page with
its own web tools and returns markdown (needs that CLI on PATH).

Choose how the agent scrapes with `--mode` (markdown / browser / extract) and a
free-form `--prompt`. The agent can use any of its tools (SERP, browser
automation, structured extraction, platform endpoints) to satisfy the prompt:

```bash
doxa ingest <url> --via hermes --mode browser
doxa ingest <url> --via hermes --mode extract --prompt "title, author, date as JSON"
```

```bash
doxa ingest https://target.example --via jina        # free, good first try for bot-walled pages
doxa ingest https://target.example --via brightdata  # needs BrightData env vars
```

For an MCP-equipped agent, two easy paths for bot-protected sources:

1. Fetch with the harness's BrightData (or other) MCP and pipe the markdown in --
   no token needed inside doxa:

```bash
printf '%s' "$FETCHED_MARKDOWN" | doxa ingest - --title "Title" --url "https://target.example"
```

2. Bridge that MCP once via the `command` fetcher so every `doxa ingest <url>`
   routes through it. Point `sources.command.argv` at a script that prints the
   fetched markdown for `{url}`:

```yaml
sources:
  fetcher: command
  command:
    argv: ["my-mcp-fetch", "{url}"]
```

## Install As A Harness Skill

Offer to register doxa as a skill for the user's harness:

```bash
doxa skill install --harness codex
doxa skill install --harness claude-code
doxa skill install --harness hermes
doxa skill install --harness openclaw
```

Use `--scope project` when the user wants project-local registration.

## Discipline

Only surface stored verbatim quotes returned by `doxa query`.

Never invent a quote, source, attribution, or belief. Treat retrieved beliefs
and linked quotes as the only ground truth. If doxa returns too little evidence,
say that the belief base does not contain enough grounded evidence and offer to
ingest more trusted sources.
