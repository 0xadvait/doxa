# Examples

Concrete, copyable starting points for doxa. The examples avoid private data,
network-dependent tests, and unsafe defaults.

## Zero-setup demo

The bundled demo uses public-domain excerpts from Emerson, Plato, and Madison.
It requires no API key, database, embeddings, or network access.

```bash
doxa demo
doxa query "self-reliance and conformity" --top 2
doxa query "examined life" --answer
```

The same files are mirrored in [`examples/demo`](demo/) so you can inspect the
JSONL source of truth:

```bash
doxa query "faction and liberty" --config examples/demo/doxa.yaml
```

## Config examples

Copy one of these to `doxa.yaml`, then edit the project name, lens, and provider
settings for your corpus.

| File | Use when |
| --- | --- |
| [`configs/openai-minimal.yaml`](configs/openai-minimal.yaml) | you want API-based mining with `OPENAI_API_KEY` |
| [`configs/fireworks-openai-compatible.yaml`](configs/fireworks-openai-compatible.yaml) | you want OpenAI-compatible mining through Fireworks or another compatible endpoint |
| [`configs/semantic-postgres.yaml`](configs/semantic-postgres.yaml) | you want optional pgvector-backed semantic/hybrid search |
| [`configs/agent-fetchers-safe.yaml`](configs/agent-fetchers-safe.yaml) | you want Claude/Codex/Hermes to fetch hard web pages without unattended bypass by default |
| [`configs/command-fetcher-argv.yaml`](configs/command-fetcher-argv.yaml) | you want to route URL fetching through a local scraper or MCP bridge |

Example:

```bash
cp examples/configs/openai-minimal.yaml doxa.yaml
export OPENAI_API_KEY=...
doxa ingest ./sources/my-essay.txt
doxa query "what does this source believe about agency?" --answer
```

## Public-domain source policy

New checked-in corpora should be public domain, pre-1929, or explicitly licensed
for redistribution. For modern/private sources, keep the text outside the repo
and ingest locally:

```bash
pbpaste | doxa ingest - --title "Private notes" --author "Me"
```

## Smoke script

[`scripts/demo_smoke.sh`](scripts/demo_smoke.sh) exercises the offline demo and
is safe to run in CI or a clean local environment:

```bash
bash examples/scripts/demo_smoke.sh
```
