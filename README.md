# doxa

```text
        .-"""-.
      .'  .-.  '.        doxa
     /   (o o)   \       little goddess of grounded belief
    |   /  ^  \   |      she accepts no prophecy
    |  |  DOXA |  |      without a quote
     \  \_____/  /
      '._     _.'        No quote, no claim.
         `---'
```

Turn the sources you trust into a belief base you can query — where every answer is pinned to a **verbatim quote**, so the model can't make things up.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)

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
doxa demo
doxa query "self-reliance and conformity" --search keyword --top 2
```

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

Create a config:

```bash
doxa init
```

`doxa init` walks you through:

- mining provider: `codex-cli`, `claude-cli`, `openai`,
  `openai-compatible` / Fireworks, or `anthropic`
- model name, when the provider needs one
- API key environment variable for API providers
- `base_url` for OpenAI-compatible providers
- lens name, description, and guiding question

Directory paths are accepted:

```bash
doxa init .
doxa init ./my-belief-base/
doxa init ./configs/research.yaml
```

Non-interactive mode is script-friendly and also activates automatically when
stdin is not a TTY:

```bash
doxa init ./doxa.yaml --yes --provider codex-cli

doxa init ./fireworks.yaml \
  --yes \
  --provider openai-compatible \
  --model accounts/fireworks/models/kimi-k2p6 \
  --lens "Extract durable claims about judgment, agency, and action."
```

Use `--force` to overwrite an existing config.

Domain preferences are optional and live in config as small 0-10 weights:

```bash
doxa domains
doxa domains set technical 8
doxa domains add finance 6
doxa domains export
```

Domains are represented as ordinary `domain:<slug>` tags on beliefs and quotes,
so old JSONL stores keep working. Retrieval also matches legacy plain tags through
`preferences.domain_aliases`; for example, `--domain crypto` can boost records
tagged `token-economics`, and `--domain relationships` can boost records tagged
`trust`.

---

## Providers

| Provider | Key? | Install | Default auth/config | Best for |
| --- | --- | --- | --- | --- |
| `codex-cli` | No | core | existing Codex CLI auth via `codex exec` | local interactive setup |
| `claude-cli` | No | core | existing Claude Code auth via `claude -p` | local interactive setup |
| `openai` | Yes | `doxa[openai]` | `OPENAI_API_KEY`, `gpt-4.1-mini` | API mining |
| `openai-compatible` / `fireworks` | Usually | `doxa[openai]` | `FIREWORKS_API_KEY` for Fireworks examples | custom/open-weight models |
| `anthropic` | Yes | `doxa[anthropic]` | `ANTHROPIC_API_KEY`, `claude-3-5-sonnet-latest` | API mining |

API providers need their key in the configured environment variable:

```bash
export OPENAI_API_KEY=...
export FIREWORKS_API_KEY=...
export ANTHROPIC_API_KEY=...
```

Fireworks example:

```yaml
llm:
  provider: openai-compatible
  model: accounts/fireworks/models/kimi-k2p6
  temperature: 0

providers:
  openai-compatible:
    base_url: https://api.fireworks.ai/inference/v1
    api_key_env: FIREWORKS_API_KEY
    model: accounts/fireworks/models/kimi-k2p6
```

Then:

```bash
export FIREWORKS_API_KEY=...
doxa ingest ./sources/essay.txt
```

CLI providers do not need API key variables, but they do require the relevant
binary on `PATH`:

```bash
command -v codex
command -v claude
```

---

## Ingest sources

All ingestion uses the configured lens and provider:

```bash
doxa ingest ./notes.txt
doxa ingest ./essay.md
doxa ingest ./paper.pdf
doxa ingest https://example.com/longform-article
doxa ingest "https://www.youtube.com/watch?v=VIDEO_ID"
printf 'Trust thyself: every heart vibrates to that iron string.' | \
  doxa ingest - --title "Self-Reliance excerpt" --author "Ralph Waldo Emerson"
```

Use another config:

```bash
doxa ingest ./sources/plato.txt --config ./configs/philosophy.yaml
```

Source support:

| Source | Requirement | Loader behavior |
| --- | --- | --- |
| stdin (`-`) | core | Reads piped UTF-8 text; use `--title`, `--author`, and `--url` for metadata. |
| `.txt`, `.md`, `.text` | core | Reads local UTF-8 text. |
| URL | core | Fetches HTML/text with the configured URL fetcher. |
| PDF | `doxa[pdf]` | Extracts page text with PyMuPDF. |
| YouTube | `doxa[youtube]` | Downloads English subtitles or auto-captions with yt-dlp. |

Ingest writes:

```text
data/beliefs.jsonl
data/quotes.jsonl
data/sources.jsonl
```

### Tough sources / BrightData

For an MCP-equipped agent, the easiest path is to fetch the tough source with
the harness's BrightData MCP, then pipe the returned markdown or text into doxa.
No BrightData token is needed inside doxa:

```bash
printf '%s' "$FETCHED_MARKDOWN" | \
  doxa ingest - --title "Article title" --url "https://target.example"
```

For direct CLI use, configure BrightData Web Unlocker env vars and override the
fetcher per ingest:

```bash
export BRIGHTDATA_API_TOKEN=...
export BRIGHTDATA_ZONE=...
doxa ingest https://target.example --via brightdata
```

Or set it in `doxa.yaml`:

```yaml
sources:
  fetcher: brightdata
  brightdata:
    api_token_env: BRIGHTDATA_API_TOKEN
    zone_env: BRIGHTDATA_ZONE
```

---

## Query

Keyword search is the default and has no infrastructure dependency:

```bash
doxa query "faction and liberty" --search keyword --limit 5
doxa query "faction and liberty" --search keyword --top 5
```

Keyword retrieval searches both belief documents and quote documents. A phrase
that appears only in a quote can retrieve the linked belief, and the matched
quote is displayed before other linked quotes.

Domain-focused queries:

```bash
doxa query "incident response tradeoffs" --domain technical
doxa query "market structure and incentives" --domains finance,policy
doxa query "plain keyword behavior" --no-domain-boost
```

Use JSON output for downstream tools:

```bash
doxa query "examined life" --json
```

Only quote what doxa returns. If retrieval returns too little evidence, ingest
more trusted sources rather than filling the gap yourself.

---

## Semantic search

Semantic and hybrid retrieval use `fastembed` plus Postgres with pgvector.

Install extras:

```bash
python -m pip install -e ".[embeddings,postgres]"
```

Prepare Postgres, enable pgvector, and set the DSN:

```bash
export DOXA_POSTGRES_DSN=postgresql://user:password@localhost:5432/doxa
psql "$DOXA_POSTGRES_DSN" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Build the index from JSONL:

```bash
doxa index
```

Query:

```bash
doxa query "political conflict as a permanent condition" --search semantic
doxa query "political conflict as a permanent condition" --search hybrid
```

`hybrid` fuses keyword and semantic rankings. If semantic search is unavailable,
hybrid reports a warning and falls back to keyword results.

---

## Faithfulness eval

Run the built-in integrity check:

```bash
doxa eval
```

Example:

```text
Beliefs: 8
Quotes: 8
Sources: 3
Checked quotes: 8
Quote verbatim: 100.00%
Bad links: 0
Orphan beliefs: 0
OK: True
```

The eval checks:

- every quote is still verbatim in stored source text
- every quote links to an existing belief
- every belief has at least one linked quote

---

## Install as an agent skill

`doxa` ships a portable skill file for agent harnesses. The skill tells the
agent to call the `doxa` CLI and treat linked quotes as ground truth. It turns
JSONL-backed corpora into custom knowledge bases for Claude Code, Codex, Hermes,
OpenCLAW, and similar tools.

```bash
doxa skill install --harness claude-code
doxa skill install --harness codex
doxa skill install --harness hermes
doxa skill install --harness openclaw
doxa skill install --harness generic --dest ./skills/doxa
```

Use `--scope project` for harnesses that support project-local skill folders:

```bash
doxa skill install --harness codex --scope project
```

The skill contract is deliberately strict: No quote, no claim.

---

## Writing a lens

A lens is the question doxa asks while reading. Keep it narrower than
"everything interesting."

Full lens:

```yaml
lens:
  name: decision-theory
  description: Extract claims about judgment, uncertainty, incentives, and action.
  question: What does this source believe about making decisions under uncertainty?
  stances:
    - supports
    - questions
    - rejects
    - complicates
  tags:
    - uncertainty
    - incentives
    - judgment
```

String shorthand is also accepted:

```yaml
lens: Extract claims about courage, duty, risk, and practical judgment.
```

String lenses use sensible defaults for name, guiding question, stances, and
tags, and are safe for ingest and prompt construction.

---

## Schema reference

`Belief`:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable belief identifier. |
| `belief` | string | Concise claim or stance. |
| `reasoning` | string | Why the linked quote supports the belief. |
| `stance` | string | Usually `supports`, `questions`, `rejects`, or `complicates`. |
| `conviction` | number | 0 to 1 score based only on quote support. |
| `tags` | list[string] | Optional retrieval/filtering tags. |
| `source` | object | `title`, `author`, `date`, `url`. |

`Quote`:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable quote identifier. |
| `quote` | string | Exact source substring. |
| `speaker` | string | Speaker or author label when available. |
| `source` | object | `title`, `author`, `date`, `url`. |
| `context` | string | Short surrounding context. |
| `tags` | list[string] | Optional quote tags. |
| `belief_ids` | list[string] | Linked belief identifiers. |

Stored source records keep the full text so quote faithfulness can be checked
again later.

Domain preferences use normal tags such as `domain:technical`, plus optional
plain-tag aliases under `preferences.domain_aliases`; no schema migration is
required.

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

**Can I inspect or edit the store directly?**

Yes. The store is line-delimited JSON. Keep quote strings verbatim if you edit
records by hand, then run `doxa eval`.

---

## Plato note

`doxa` is Greek for belief, opinion, or what seems to be the case.

---

## Contributing

Public-domain or explicitly licensed examples only. Do not add private corpora,
API keys, generated secrets, or network-dependent tests. Keep core dependencies
minimal and make optional integrations explicit through extras.

Run:

```bash
python -m pytest -q
doxa demo
doxa query "self-reliance and conformity" --search keyword
```

Licensed under the MIT License. See [LICENSE](LICENSE).
