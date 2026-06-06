<div align="center">

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/orb_light.png">
  <img alt="doxa" src="assets/orb_dark.png" width="200">
</picture>

# doxa

**belief oracle** &nbsp;&middot;&nbsp; quote-first knowledge for agents &nbsp;&middot;&nbsp; no quote, no claim

<p>
  <a href="https://x.com/advait_jayant"><img src="https://img.shields.io/twitter/follow/advait_jayant?style=social" alt="Follow @advait_jayant"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
</p>

</div>

---

Turn the sources you trust into a belief base you can query — where every answer is pinned to a **verbatim quote**, so the model can't make things up.

Most "chat with your notes" tools let an LLM paraphrase your sources and quietly invent the rest. doxa doesn't. It mines essays, PDFs, web pages, and transcripts into two linked records — a concise **belief** and the **exact quote** that grounds it. You query the beliefs; every answer traces back to real source text. No quote, no claim.

- **Verbatim-grounded** — every belief links to an exact source quote; quotes are never model-generated.
- **Agent-ready custom knowledge bases** — install as a skill for Claude Code, Codex, Hermes, OpenCLAW, or another CLI-capable harness.
- **Local and portable** — a plain JSONL source of truth you can read, diff, and re-index.
- **Any lens, any model** — mine a source through your perspective, with codex-cli / claude-cli (no API key) or OpenAI / Fireworks / Anthropic.
- **Quote-first retrieval** — keyword search indexes belief docs and quote docs, then folds quote hits back to linked beliefs.
- **Domain preferences** — small 0-10 domain weights steer mining tags and retrieval boosts without changing JSONL schema. Alias terms keep older plain tags useful.
- **Keyword → semantic → hybrid** — works with zero setup; add embeddings when you want them.

**For AI agents:** start with [AGENTS.md](AGENTS.md); install as a harness skill via [skill/SKILL.md](skill/SKILL.md).

---

## Quickstart

```bash
python -m pip install -e .
doxa                  # banner + a quick-start landing
doxa guide            # full walkthrough, any time
doxa demo             # try it on bundled public-domain data
doxa query "self-reliance and conformity" --top 2
```

New to the CLI? Just run `doxa` (or `doxa guide`). `doxa status` shows where
things stand -- your config, data location, and belief/quote counts. Every
command takes `-h` for its options.

`doxa banner` defaults to `--color auto`: ANSI accents appear in an interactive
terminal, while pipes, captures, and test runs stay plain. Use `--color always`
or `--color never` to override it.

With no `doxa.yaml` in the current directory, `doxa query` uses the bundled
public-domain demo data from Emerson's "Self-Reliance", Plato's "Apology", and
Madison's "Federalist No. 10".

Example:

```text
1. Personhood requires resisting social conformity.
   stance=supports conviction=0.91 score=13.1877
   source=Self-Reliance / Ralph Waldo Emerson / 1841
   quote="Ralph Waldo Emerson: Whoso would be a man must be a nonconformist."
2. Self-trust is a necessary starting point for thought and action.
   stance=supports conviction=0.93 score=11.6399
   source=Self-Reliance / Ralph Waldo Emerson / 1841
   quote="Ralph Waldo Emerson: Trust thyself: every heart vibrates to that iron string."
```

Keyword search works with no API key, database, embedding model, or network.

---

## Docs

- [Configuration](docs/configuration.md) · [Providers](docs/providers.md) · [Ingestion](docs/ingestion.md)
- [Retrieval](docs/retrieval.md) · [Writing a lens](docs/writing-a-lens.md) · [Architecture](docs/architecture.md)
- [Agent skill](docs/skill.md) · [AGENTS.md](AGENTS.md) · [skill/SKILL.md](skill/SKILL.md)

---

## Example questions & answers

These examples are from the bundled public-domain demo and were generated with
`--search keyword`. Keyword is the default, so the reproduce lines use the
shorter command form.

<details>
<summary>Should I trust my own judgment over the crowd?</summary>

The demo retrieves Emerson's belief that self-trust is necessary, but it also surfaces a real Socratic tension: confidence in judgment should be held alongside intellectual humility.

`source=Self-Reliance / Ralph Waldo Emerson / 1841`
`quote="Ralph Waldo Emerson: Trust thyself: every heart vibrates to that iron string."`

`source=Apology / Plato, translated by Benjamin Jowett / 1892`
`quote="Socrates: I know that I have no wisdom, small or great."`

Reproduce: `doxa query "Should I trust my own judgment over the crowd?"`

</details>

<details>
<summary>Is it rational to fear death?</summary>

The demo grounds Socrates' answer in the belief that a good person need not fear ultimate harm from death.

`source=Apology / Plato, translated by Benjamin Jowett / 1892`
`quote="Socrates: Wherefore, O judges, be of good cheer about death, and know of a certainty, that no evil can happen to a good man, either in life or after death."`

Reproduce: `doxa query "Is it rational to fear death?"`

</details>

<details>
<summary>Should a republic eliminate liberty to stop faction?</summary>

Madison complicates the idea: liberty feeds faction, but the retrieved belief says liberty is not a condition a republic can simply extinguish.

`source=Federalist No. 10 / James Madison / 1787`
`quote="James Madison: Liberty is to faction what air is to fire, an aliment without which it instantly expires."`

`source=Federalist No. 10 / James Madison / 1787`
`quote="James Madison: The latent causes of faction are thus sown in the nature of man."`

Reproduce: `doxa query "Should a republic eliminate liberty to stop faction?"`

</details>

<details>
<summary>What is the highest standard for the mind?</summary>

The demo answers through Emerson: the highest retrieved standard is the integrity of one's own mind.

`source=Self-Reliance / Ralph Waldo Emerson / 1841`
`quote="Ralph Waldo Emerson: Nothing is at last sacred but the integrity of your own mind."`

Reproduce: `doxa query "What is the highest standard for the mind?"`

</details>

<details>
<summary>What makes a life worth living?</summary>

The demo retrieves Socrates' belief that a worthy life requires examination.

`source=Apology / Plato, translated by Benjamin Jowett / 1892`
`quote="Socrates: The unexamined life is not worth living."`

Reproduce: `doxa query "What makes a life worth living?"`

</details>

---

## Why doxa exists

Fluency is where hallucinations hide: a summarizer can compress, overstate,
merge claims, or invent wording that was never in the source. doxa trades a
little fluency for a guarantee you can audit.

`doxa` takes a stricter approach:

- A `Belief` is a distilled claim, stance, value, or reason.
- A `Quote` is an exact source substring that grounds one or more beliefs.
- After mining, doxa checks every proposed quote against the original source
  text with whitespace-normalized verbatim matching.
- Quotes that are not actually present are dropped before they enter the store.
- Beliefs without surviving quote links are dropped too.

The other difference is the lens. You define what kind of belief you want to
mine. A strategy lens, legal lens, philosophical lens, and product lens can all
read the same source and produce different belief bases.

---

## How it works

```text
 text / PDF / URL / YouTube / notes
                |
                v
        mine [provider + lens]
                |
                v
      JSON beliefs + verbatim quotes
                |
                v
 JSONL source of truth (+ optional pgvector index)
                |
                v
 keyword / semantic / hybrid retrieve
                |
                v
 grounded answer with linked quotes
```

JSONL is the durable source of truth. Postgres/pgvector is optional and can be
rebuilt from JSONL at any time.

---

## Install

Core install is intentionally small. It supports config loading, demo data,
keyword retrieval, evaluation, and plain text / URL ingestion:

```bash
python -m pip install -e .
```

Install every optional runtime integration:

```bash
python -m pip install -e ".[all]"
```

Install by requirements file instead:

```bash
python -m pip install -r requirements.txt
```

For test/dev work:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Extras are also available individually:

```bash
python -m pip install -e ".[embeddings,postgres]"
python -m pip install -e ".[pdf,youtube]"
python -m pip install -e ".[openai,anthropic]"
```

| Extra | Adds | Used by |
| --- | --- | --- |
| core | `PyYAML` | config, demo, keyword query, eval |
| `embeddings` | `fastembed` | semantic vectors |
| `postgres` | `psycopg2-binary`, `pgvector` | pgvector indexing/search |
| `pdf` | `PyMuPDF` | PDF ingestion |
| `youtube` | `yt-dlp` | YouTube transcript ingestion |
| `openai` | `openai` | OpenAI and OpenAI-compatible mining |
| `anthropic` | `anthropic` | Anthropic mining |

---

## Configure

```bash
doxa init            # interactive: provider, model, lens -> writes doxa.yaml
doxa status          # config, data dir, belief/quote counts, provider, semantic
```

`doxa init` is also scriptable (`--yes --provider ... --model ... --lens "..."`),
and domain weights tune retrieval (`doxa domains set technical 8`). Full options:
[docs/configuration.md](docs/configuration.md).

---

## Providers

| Provider | Key? | Best for |
| --- | --- | --- |
| `codex-cli` / `claude-cli` | No (reuses your CLI login) | local interactive setup |
| `openai` | `OPENAI_API_KEY` | API mining |
| `openai-compatible` / `fireworks` | usually a key | custom / open-weight models |
| `anthropic` | `ANTHROPIC_API_KEY` | API mining |

Setup + the Fireworks example: [docs/providers.md](docs/providers.md).

---

## Ingest sources

```bash
doxa ingest ./essay.md ./paper.pdf            # files (shell globs work)
doxa ingest https://example.com/article       # URL
doxa ingest "https://youtube.com/watch?v=..." # video (yt-dlp transcript)
pbpaste | doxa ingest - --title "Notes"       # stdin
```

| Source | Requirement |
| --- | --- |
| text / stdin / URL | core |
| PDF | `doxa[pdf]` |
| YouTube | `doxa[youtube]` |

Quotes that aren't verbatim in the source are dropped. Re-ingest is skipped by
default (`--reingest` to replace); `doxa sources list` / `doxa sources remove <id>`
manage the base. Full guide: [docs/ingestion.md](docs/ingestion.md).

### Web fetchers (pluggable)

Not tied to one scraper -- pick per ingest with `--via`, or set `sources.fetcher`:

| Fetcher | Key? | What it does |
| --- | --- | --- |
| `requests` | No | plain HTTP + HTML extraction (default) |
| `jina` | optional | clean markdown, free |
| `firecrawl` | `FIRECRAWL_API_KEY` | scrape API |
| `brightdata` | tokens | Web Unlocker |
| `command` | -- | run ANY tool / MCP bridge |
| `claude` / `codex` / `hermes` | -- | a coding agent browses for you |

```bash
doxa ingest <url> --via jina                          # free, clean markdown
doxa ingest <url> --via hermes --mode browser         # render JS, then markdown
doxa ingest <url> --via codex --mode extract --prompt "name, price as JSON"
```

Agent fetchers run safely by default; add `--yolo` for unattended bypass on
trusted sources. The `command` fetcher and `register_fetcher()` wire anything
else. Full details: [docs/ingestion.md](docs/ingestion.md).

---

## Query

```bash
doxa query "faction and liberty"            # keyword (default, zero setup)
doxa query "examined life" --answer         # readable evidence brief
doxa query "examined life" --json           # machine output
doxa query "..." --top 10 --domain policy   # more results, topic-biased
```

Keyword search covers belief and quote text (a phrase only in a quote still finds
its belief). Only quote what doxa returns. Full reference + semantic/hybrid setup:
[docs/retrieval.md](docs/retrieval.md).

---

## Semantic search (optional)

```bash
python -m pip install -e ".[embeddings,postgres]"
export DOXA_POSTGRES_DSN=postgresql://...     # then enable pgvector: CREATE EXTENSION vector
doxa index
doxa query "political conflict" --search hybrid
```

Hybrid fuses keyword + semantic and falls back to keyword if the index is
unavailable. Details: [docs/retrieval.md](docs/retrieval.md).

---

## Faithfulness eval

```bash
doxa eval      # every quote still verbatim, every belief still linked (exit !=0 on failure)
doxa doctor    # config, storage, provider, and semantic-index readiness
```

---

## Use it as an agent skill

doxa ships a portable skill so an agent calls the CLI and treats quotes as ground
truth:

```bash
doxa skill install --harness claude-code   # or codex / hermes / openclaw / generic
```

Details: [docs/skill.md](docs/skill.md) and [AGENTS.md](AGENTS.md).

---

## Lens & schema

A **lens** is the question doxa asks while reading (narrow beats broad) --
[docs/writing-a-lens.md](docs/writing-a-lens.md). Beliefs and quotes are plain
JSONL; field reference in [docs/schema.md](docs/schema.md).

---

## FAQ

**Does doxa prevent all hallucinations?**

It prevents non-verbatim quotes from entering the store. The interpretation in a
belief can still be too broad or too narrow, so keep lenses crisp and run
`doxa eval`.

**Do I need Postgres?**

No. Keyword retrieval is pure Python and works out of the box. Postgres/pgvector
is only for semantic and hybrid search.

**Which provider should I start with?**

Use `codex-cli` if you already use Codex CLI. Use `claude-cli` if you already
use Claude Code. Use OpenAI, Fireworks, or Anthropic when you want API-based
mining in scripts or services.

**Where is my data stored?**

By default, next to `doxa.yaml` under `data/*.jsonl`. API providers receive the
source chunks you ingest, so choose providers according to your data policy.

**Can I inspect, update, or remove what I've ingested?**

Yes. `doxa sources list` shows every ingested source with its belief/quote
counts; `doxa sources remove <id>` deletes a source and its rows; re-ingesting
replaces a source with `--reingest`. The store is also plain line-delimited JSON
you can edit by hand -- keep quote strings verbatim, then run `doxa eval` (and
`doxa index` if you use semantic search) to re-check and rebuild.

---

## Troubleshooting

- **"Config not found"** -- run `doxa init` here, or point at one with `--config <path>`.
- **"Set OPENAI_API_KEY / ..."** -- export the key, or switch to a no-key provider: `doxa init --provider codex-cli`.
- **"needs the Codex/Claude CLI on PATH"** -- install that CLI, or pick another provider with `doxa init`.
- **Semantic / `doxa index` errors** -- check `DOXA_POSTGRES_DSN` points at a running Postgres with pgvector enabled (`CREATE EXTENSION vector` as a superuser/owner). `doxa status` shows whether semantic is ready.
- **Querying the wrong data?** -- with no `doxa.yaml` present, doxa uses the bundled demo base and says so on stderr. `doxa status` shows the active config and counts.
- **See the full traceback** for a bug report: set `DOXA_DEBUG=1` before the command.

---

## Plato note

`doxa` is Greek for belief, opinion, or what seems to be the case.

---

## Contributing

Public-domain or explicitly licensed examples only. Do not add private corpora,
API keys, generated secrets, or network-dependent tests. Keep core dependencies
minimal and make optional integrations explicit through extras.

The terminal banner (`doxa/_assets/banner.txt`) is generated from the source art
in `assets/` -- the DOXA wordmark is half-block, the oracle orb is braille. To
regenerate it after changing the art, run `python3 tools/build_banner.py`
(needs Pillow).

Run:

```bash
python -m pytest -q
doxa demo
doxa query "self-reliance and conformity" --search keyword
doxa query "self-reliance and conformity" --search keyword --answer
```

Licensed under the MIT License. See [LICENSE](LICENSE).
