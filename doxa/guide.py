"""Human-facing onboarding copy for the terminal.

doxa is built to be driven by an AI agent (see ``doxa skill install``), which
onboards from ``SKILL.md``. A human at a prompt needs more hand-holding: a
first-run landing, a guided walkthrough, and clear next steps. That copy lives
here so the CLI stays thin and the wording stays in one place.
"""

from __future__ import annotations

_RESET = "\033[0m"
_BOLD = "\033[1m"
_ACCENT = "\033[38;5;81m"      # cyan, matches the banner orb
_DIM = "\033[38;5;245m"


def _style(text: str, code: str, color: bool) -> str:
    return f"{code}{text}{_RESET}" if color else text


def overview_text(color: bool = False) -> str:
    """Short landing shown under the banner on a bare ``doxa`` invocation."""

    def h(text: str) -> str:
        return _style(text, _BOLD + _ACCENT, color)

    def d(text: str) -> str:
        return _style(text, _DIM, color)

    return "\n".join(
        [
            "doxa -- a queryable belief base where every answer is pinned to a",
            "verbatim quote, so the model can't make things up. For you and your agents.",
            "",
            h("New here?  Three steps to your first grounded answer:"),
            "  1.  doxa demo                  " + d("see it work on bundled demo data"),
            "  2.  doxa init                  " + d("create your own base (writes doxa.yaml)"),
            "  3.  doxa ingest <file|url|->   " + d("mine a source into beliefs + quotes"),
            '      doxa query \"<question>\"    ' + d("ask -- every answer cites a real quote"),
            "",
            h("Driving doxa from an AI agent?  (Claude Code, Codex, Hermes ...)"),
            "  doxa skill install --harness claude-code   " + d("then just ask the agent"),
            "",
            h("There's more than the basics -- a quick tour:"),
            "  doxa packs install startup-wisdom   " + d("a ready-made founder/product/growth base"),
            "  doxa lenses list      " + d("opinionated lenses: founder, investment, research ..."),
            "  doxa ingest <url> --via jina   " + d("fetch hard pages (jina/firecrawl/brightdata/agent)"),
            "  doxa query --answer | --json | --search hybrid   " + d("brief | machine | semantic"),
            "  doxa eval | doxa doctor   " + d("verify every quote | check your setup"),
            "  " + d("full tour:  doxa guide"),
            "",
            h("More"),
            "  doxa guide    " + d("guided walkthrough") + "       doxa status   " + d("where things stand"),
            "  doxa --help   " + d("every command") + "            doxa <cmd> -h  " + d("help for one command"),
        ]
    )


def guide_text(color: bool = False) -> str:
    """Full walkthrough shown by ``doxa guide``."""

    def h(text: str) -> str:
        return _style(text, _BOLD + _ACCENT, color)

    def t(text: str) -> str:
        return _style(text, _BOLD, color)

    def d(text: str) -> str:
        return _style(text, _DIM, color)

    return "\n".join(
        [
            t("doxa // belief oracle -- a guided tour"),
            "",
            "",
            h("WHAT IT IS"),
            "",
            "  doxa turns sources you trust into two linked records:",
            "",
            "    - a belief : a concise claim, stance, or value distilled from the source",
            "    - a quote  : the exact words from the source that back that belief",
            "",
            "  You query the beliefs; every answer carries the verbatim quote behind it.",
            "  The rule it enforces:  " + t("no quote, no claim") + ".",
            "",
            "",
            h("THE LOOP"),
            "",
            "  " + t("1. doxa demo"),
            "        Explore a bundled, public-domain base (Emerson, Plato, Madison) to",
            "        see the shape of a result before building your own.",
            "",
            "  " + t("2. doxa init"),
            "        Walks you through a doxa.yaml: which model mines your sources (the",
            "        \"provider\") and the \"lens\" -- the kind of beliefs you want extracted.",
            "        " + d("codex-cli / claude-cli need no API key (they reuse your existing"),
            "        " + d("Codex / Claude login). openai / fireworks / anthropic need a key."),
            "        " + d("Not sure which lens? `doxa lenses list` and start from a template:"),
            "        " + d("doxa init --lens-template founder-strategy"),
            "",
            "  " + t("3. doxa ingest <source>"),
            "        Mine a source into beliefs + quotes. A source can be:",
            "",
            "          a file      doxa ingest ./essay.md",
            "          a PDF       doxa ingest ./paper.pdf",
            "          a web page  doxa ingest https://example.com/article",
            "          a video     doxa ingest \"https://youtube.com/watch?v=...\"",
            "          stdin       pbpaste | doxa ingest - --title \"Notes\"",
            "",
            "        " + d("Quotes that aren't verbatim in the source are dropped automatically."),
            "",
            "  " + t("4. doxa query \"<question>\""),
            "        Retrieve the most relevant beliefs and their quotes. Add --answer for",
            "        a clean evidence brief, --json for machine output, --domain <slug> to",
            "        bias toward a topic, --search hybrid after you build the semantic index.",
            "",
            "  " + t("5. doxa eval"),
            "        Check the base: every quote still verbatim, every link intact.",
            "",
            "",
            h("WHERE THINGS LIVE"),
            "",
            "  Your beliefs and quotes are plain JSONL under the data/ dir beside your",
            "  doxa.yaml -- readable, diffable, yours. Run " + t("doxa status") + " to see counts.",
            "",
            "",
            h("THE FULL TOOLBOX"),
            "",
            "  " + t("Starter packs") + " -- skip the empty base; install a curated one:",
            "      doxa packs list                  " + d("ready-made bases (e.g. startup-wisdom)"),
            "      doxa packs install startup-wisdom " + d("~14k founder/product/growth beliefs + quotes"),
            "",
            "  " + t("Lenses") + " -- you don't have to invent one; start from the library:",
            "      doxa lenses list                 " + d("8 opinionated lenses + your own"),
            "      doxa lenses show investment-memo  " + d("see one before you use it"),
            "      doxa init --lens-template founder-strategy",
            "      doxa lenses add my-lens --from founder-strategy   " + d("fork + make it yours"),
            "",
            "  " + t("Ingest anything") + " -- the URL fetcher is pluggable (--via):",
            "      doxa ingest <url> --via jina      " + d("free clean markdown (firecrawl/brightdata too)"),
            "      doxa ingest <url> --via hermes --mode browser    " + d("agent renders JS, then mines"),
            "      doxa ingest <url> --via codex --mode extract --prompt \"...\"",
            "      doxa ingest <url> --via codex --yolo   " + d("unattended agent fetch (trusted sources)"),
            "      doxa ingest f.pdf | \"https://youtu.be/...\" | -   " + d("PDFs, video transcripts, stdin"),
            "",
            "  " + t("Ask, your way:"),
            "      doxa query \"...\" --answer        " + d("readable evidence brief"),
            "      doxa query \"...\" --json          " + d("structured, for tools/agents"),
            "      doxa query \"...\" --domain founders --top 10",
            "      doxa query \"...\" --search hybrid " + d("semantic + keyword (after doxa index)"),
            "",
            "  " + t("Keep it honest:"),
            "      doxa eval     " + d("every quote still verbatim, every belief still linked"),
            "      doxa doctor   " + d("config, storage, provider, semantic readiness"),
            "      doxa sources list | remove <id>   " + d("see / undo what you ingested"),
            "      doxa domains set founders 8       " + d("bias retrieval toward a topic"),
            "",
            "",
            h("FOR AI AGENTS"),
            "",
            "  doxa is built to be driven by an agent. Install the skill and your agent",
            "  learns to call doxa and treat the quotes as ground truth:",
            "",
            "    doxa skill install --harness claude-code   " + d("# or codex / hermes / openclaw"),
            "",
            d("Run any command with -h for its full options.  Full docs: README.md"),
        ]
    )
