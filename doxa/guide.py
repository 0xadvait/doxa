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
            h("WHAT IT IS"),
            "  doxa turns sources you trust into two linked records:",
            "    - a belief : a concise claim, stance, or value distilled from the source",
            "    - a quote  : the exact words from the source that back that belief",
            "  You query the beliefs; every answer carries the verbatim quote behind it.",
            "  The rule it enforces:  " + t("no quote, no claim") + ".",
            "",
            h("THE LOOP"),
            "  " + t("1. doxa demo"),
            "       Explore a bundled, public-domain base (Emerson, Plato, Madison) to",
            "       see the shape of a result before building your own.",
            "",
            "  " + t("2. doxa init"),
            "       Walks you through a doxa.yaml: which model mines your sources (the",
            "       \"provider\") and the \"lens\" -- the kind of beliefs you want extracted.",
            "       " + d("codex-cli / claude-cli need no API key (they reuse your existing"),
            "       " + d("Codex / Claude login). openai / fireworks / anthropic need a key."),
            "",
            "  " + t("3. doxa ingest <source>"),
            "       Mine a source into beliefs + quotes. A source can be:",
            "         a file      doxa ingest ./essay.md",
            "         a PDF       doxa ingest ./paper.pdf",
            "         a web page  doxa ingest https://example.com/article",
            "         a video     doxa ingest \"https://youtube.com/watch?v=...\"",
            "         stdin       pbpaste | doxa ingest - --title \"Notes\"",
            "       " + d("Quotes that aren't verbatim in the source are dropped automatically."),
            "",
            "  " + t("4. doxa query \"<question>\""),
            "       Retrieve the most relevant beliefs and their quotes. Add --answer for",
            "       a readable summary, --json for machine output, --search hybrid after",
            "       you build the optional semantic index (doxa index).",
            "",
            "  " + t("5. doxa eval"),
            "       Check the base: every quote still verbatim, every link intact.",
            "",
            h("WHERE THINGS LIVE"),
            "  Your beliefs and quotes are plain JSONL under the data/ dir beside your",
            "  doxa.yaml -- readable, diffable, yours. Run " + t("doxa status") + " to see counts.",
            "",
            h("FOR AI AGENTS"),
            "  doxa is built to be driven by an agent. Install the skill and your agent",
            "  learns to call doxa and treat the quotes as ground truth:",
            "    doxa skill install --harness claude-code   " + d("# or codex / hermes / openclaw"),
            "",
            d("Run any command with -h for its full options.  Full docs: README.md"),
        ]
    )
