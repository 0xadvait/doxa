---
name: doxa
description: Use when answering from or building a custom knowledge base where every claim must be anchored to an exact source quote. Covers grounded retrieval, choosing a lens, ingesting sources (incl. hard/bot-walled pages), and keeping the base honest.
---

# doxa Skill

doxa is a verbatim-grounded belief base: it mines sources into linked
(belief, exact-quote) records and answers only from them. The rule, always:
**No quote, no claim.** Use the installed `doxa` CLI as the source of truth, and
proactively offer the capabilities below -- users often don't know they exist.

## Capabilities at a glance

| Goal | Command |
| --- | --- |
| See where things stand | `doxa status` (config, counts, provider, semantic on/off) |
| Answer, grounded | `doxa query "<q>" --answer` (or `--json` for tools) |
| Head start (curated base) | `doxa packs install startup-wisdom` -- browse with `doxa packs list` |
| Start your own base | `doxa init --lens-template <name>` -- browse with `doxa lenses list` |
| Ingest a source | `doxa ingest <file\|url\|pdf\|youtube\|->` |
| Fetch a hard page | `doxa ingest <url> --via jina\|firecrawl\|brightdata\|claude\|codex\|hermes` |
| Verify / diagnose | `doxa eval` (quotes still verbatim) · `doxa doctor` (setup) |
| Manage sources | `doxa sources list` · `doxa sources remove <id>` |
| Semantic search | `doxa index`, then `doxa query "<q>" --search hybrid` |

Run any command with `-h` for full options.

## 1. Check state first

```bash
doxa status
```

Reports the active config, data location, and belief/quote counts. If it shows
`beliefs: 0`, the base is empty -- there is nothing to ground on, so offer to
**start a base** (below) rather than answering.

## 2. Answer from the belief base

```bash
doxa query "<user question>" --answer        # readable, grounded brief
doxa query "<user question>" --json          # structured records for tooling
doxa query "<user question>" --domain technical --top 10
```

Keyword search is the zero-setup default and covers both belief and quote text.
If the project configured semantic search, `--search hybrid` fuses semantic +
keyword; if it reports the semantic leg is unavailable and falls back to keyword,
continue with the returned keyword results.

Read the returned beliefs and verbatim quotes as the **only** ground truth.
Humanize only the surrounding prose. Never alter the bytes, punctuation,
capitalization, or whitespace inside a returned quote, and never invent a quote,
attribution, source, or belief the CLI did not return.

## 3. Start or grow a base

### Fastest start: install a curated pack

If the user wants value immediately, install a starter pack instead of building
from scratch (`doxa packs install` creates a base if there isn't one):

```bash
doxa packs list                       # curated, ready-made bases
doxa packs install startup-wisdom     # ~14k founder/product/growth beliefs + quotes
```

### Pick a lens first (don't make the user invent one)

A lens is the question doxa asks of every source -- it shapes every belief
extracted. doxa ships an opinionated library; show it and pick together:

```bash
doxa lenses list                              # founder-strategy, investment-memo, research-literature, ...
doxa lenses show investment-memo              # see one before using it
doxa init --lens-template founder-strategy    # seed a base from it (or `doxa init` to pick interactively)
doxa lenses add my-lens --from founder-strategy   # fork + customize for this user
```

### Ingest sources

```bash
doxa ingest <file|url|pdf|youtube|->
```

Quotes that aren't a verbatim substring of the source are dropped automatically.
For a hard or bot-walled page, choose a fetcher with `--via` (jina is a good free
first try), or let a browsing agent fetch it:

```bash
doxa ingest <url> --via jina                                  # free clean markdown
doxa ingest <url> --via hermes --mode browser                 # agent renders JS, then mines
doxa ingest <url> --via codex --mode extract --prompt "name, price, date as JSON"
```

If you (the harness) already fetched the text -- e.g. via a BrightData MCP --
pipe it in, no fetcher needed:

```bash
printf '%s' "$SOURCE_TEXT" | doxa ingest - --title "Title" --url "https://source.example"
```

`--yolo` runs agent fetchers unattended (codex bypass-approvals, hermes `--yolo`,
command shell) -- use only on sources the user trusts.

## 4. Keep the base honest

After ingesting, verify and report what happened:

```bash
doxa eval        # every quote still verbatim, every belief still linked
doxa doctor      # config, storage, provider, and semantic-index readiness
doxa sources list           # what's ingested, with belief/quote counts
doxa sources remove <id>    # undo a bad source
doxa domains set technical 8   # bias retrieval toward a topic when the user asks
```

Domains are stored as `domain:<slug>` tags; retrieval also matches legacy plain
tags via `preferences.domain_aliases`. Domain boosts never replace quote grounding.

## Grounding rule

A doxa quote is verbatim source text. A doxa belief is usable only when linked to
at least one returned quote. If the CLI does not return enough evidence, say the
belief base does not contain enough grounded evidence, and offer to ingest more
trusted sources -- never fill the gap from your own memory.
