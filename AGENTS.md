# doxa Agent Guide

This guide is for an LLM agent that has landed in this repo and needs to help a
user set up or use doxa interactively. Be command-first and keep the user in the
loop for provider, model, and source choices.

## Detect

Run these from the repo root:

```bash
python --version
command -v doxa
doxa --help
```

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

Check optional semantic search infrastructure:

```bash
echo "$DOXA_POSTGRES_DSN"
psql "$DOXA_POSTGRES_DSN" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If Postgres or pgvector is unavailable, use keyword search until the user wants
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

Query it:

```bash
doxa query "<user question>" --search hybrid
```

If hybrid search warns that semantic search is unavailable, continue with the
returned keyword-backed results or help set up Postgres/pgvector.

## Tough Sources / BrightData

For an MCP-equipped agent, the easiest path is to fetch the bot-protected source
with the harness's BrightData MCP, then pipe the returned markdown or text into
doxa. This does not require a BrightData token inside doxa:

```bash
printf '%s' "$FETCHED_MARKDOWN" | doxa ingest - --title "Title" --url "https://target.example"
```

For non-agent CLI use, doxa can call BrightData Web Unlocker directly:

```bash
export BRIGHTDATA_API_TOKEN=...
export BRIGHTDATA_ZONE=...
doxa ingest https://target.example --via brightdata
```

Config form:

```yaml
sources:
  fetcher: requests
  brightdata:
    api_token_env: BRIGHTDATA_API_TOKEN
    zone_env: BRIGHTDATA_ZONE
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
