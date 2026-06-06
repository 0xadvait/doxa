# doxa as an Agent Skill

For full interactive agent setup, see [AGENTS.md](../AGENTS.md). The portable
skill lives at [skill/SKILL.md](../skill/SKILL.md). It is harness-neutral: the
skill does not import Python modules or assume a specific agent runtime. It
shells out to the installed `doxa` CLI.

doxa works well as a custom knowledge base for Claude Code, Codex, Hermes,
OpenCLAW, and similar harnesses because the agent never has to trust an
ungrounded summary. The rule is simple: No quote, no claim.

## Install

Prerequisite: install the `doxa` CLI before installing the skill. From a local
checkout, run:

```bash
python -m pip install -e ".[all]"
```

```bash
doxa skill install --harness claude-code
doxa skill install --harness codex
doxa skill install --harness hermes
doxa skill install --harness openclaw
doxa skill install --harness generic --dest ./skills/doxa
```

The installer creates the target directory if needed and overwrites the target
`SKILL.md` file.

Defaults are intentionally simple and easy to extend:

- Claude Code user scope: `~/.claude/skills/doxa/SKILL.md`
- Claude Code project scope: `./.claude/skills/doxa/SKILL.md`
- Codex user scope: `~/.codex/skills/doxa/SKILL.md`
- Codex project scope: `./.codex/skills/doxa/SKILL.md`
- Hermes user scope: `~/.hermes/skills/doxa/SKILL.md`
- Hermes project scope: `./.hermes/skills/doxa/SKILL.md`
- OpenCLAW user scope: `~/.openclaw/skills/doxa/SKILL.md`
- OpenCLAW project scope: `./.openclaw/skills/doxa/SKILL.md`

For an unknown harness, use `--harness generic --dest <dir>` and point the
harness at that directory.

## Runtime behavior

For answers, the skill tells the agent to run:

```bash
doxa query "<question>" --search keyword
```

For final prose, the agent can use the deterministic local renderer:

```bash
doxa query "<question>" --search keyword --answer
```

The agent may add domain focus when useful:

```bash
doxa query "<question>" --search keyword --domain technical
doxa query "<question>" --search keyword --domains policy,finance
```

Keyword search is the zero-setup default. Use `--search hybrid` only when the
project has optional semantic search configured; if semantic search is
unavailable, hybrid prints a warning and falls back to keyword results.

For growth, it tells the agent to run:

```bash
doxa ingest <source>
```

For source text already fetched by the harness, including via a BrightData MCP:

```bash
printf '%s' "$FETCHED_TEXT" | doxa ingest - --title "Title" --url "https://source.example"
```

The returned beliefs and quotes are the only ground truth. The agent must not
invent quotes, sources, attributions, or claims. It may smooth the connective
prose, but returned quote spans must be copied exactly, including punctuation,
capitalization, and whitespace. If retrieval is thin, the agent should say that
the belief base does not contain enough grounded evidence and offer to ingest
more trusted sources.
