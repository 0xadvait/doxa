---
name: doxa
description: Use when answering from or growing a custom knowledge base where every belief must be anchored to exact source quotes.
---

# doxa Skill

Use the installed `doxa` CLI as the source of truth for grounded beliefs in a
custom knowledge base. No quote, no claim.

## Answer from the belief base

Run:

```bash
doxa query "<user question>" --search hybrid
```

Use domain focus only when it is clearly relevant to the user's question:

```bash
doxa query "<user question>" --search hybrid --domain technical
doxa query "<user question>" --search hybrid --domains policy,finance
```

Read the returned beliefs and verbatim quotes as the only ground truth. Answer
from those returned records. Cite or include the exact quotes when they matter.
Never invent a quote, attribution, source, or belief that was not returned by
the CLI.

If hybrid search reports that the semantic leg is unavailable and falls back to
keyword, continue with the returned keyword-grounded results.

## Grow the belief base

When the user wants to add a trusted source, run:

```bash
doxa ingest <source>
```

`<source>` may be a text file, PDF, article URL, or YouTube URL depending on the
installed doxa extras. Ingestion mines beliefs through the configured provider
and drops any quote that cannot be verified as a real substring of the source.

If the source text has already been fetched by the harness, pipe it through
stdin and attach metadata:

```bash
printf '%s' "$SOURCE_TEXT" | doxa ingest - --title "Title" --url "https://source.example"
```

For bot-protected sources, prefer a harness BrightData MCP fetch followed by
`doxa ingest -`. Direct CLI use can route through BrightData with
`doxa ingest <url> --via brightdata` when `BRIGHTDATA_API_TOKEN` and
`BRIGHTDATA_ZONE` are set.

## Domain preferences

To inspect domain weights:

```bash
doxa domains
```

To adjust them when the user asks:

```bash
doxa domains set technical 8
doxa domains add finance 6
doxa domains remove creative
```

Domains are stored as `domain:<slug>` tags on beliefs and quotes. Retrieval also
uses `preferences.domain_aliases` so legacy plain tags such as `founders`,
`token-economics`, `trust`, or `taste` can boost the requested domain. Domain
boosts do not replace quote grounding.

## Grounding rule

A doxa quote is verbatim source text. A doxa belief is usable only when linked
to at least one returned quote. If the CLI does not return enough evidence,
state that the belief base does not contain enough grounded evidence.
