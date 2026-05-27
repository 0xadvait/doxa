# doxa as an Agent Skill

For full interactive agent setup, see [AGENTS.md](../AGENTS.md). The portable
skill lives at [skill/SKILL.md](../skill/SKILL.md). It is harness-neutral: the
skill does not import Python modules or assume a specific agent runtime. It
shells out to the installed `doxa` CLI.

## Install

```bash
doxa skill install --harness claude-code
doxa skill install --harness codex
doxa skill install --harness hermes
doxa skill install --harness openclaw
doxa skill install --harness generic --dest ./skills/doxa
```

Defaults are intentionally simple and easy to extend:

- Claude Code user scope: `~/.claude/skills/doxa/SKILL.md`
- Codex user scope: `~/.codex/skills/doxa/SKILL.md`
- Hermes user scope: `~/.hermes/skills/doxa/SKILL.md`
- OpenCLAW user scope: `~/.openclaw/skills/doxa/SKILL.md`
- Project scope uses `./.<harness>/skills/doxa/SKILL.md`

For an unknown harness, use `--harness generic --dest <dir>` and point the
harness at that directory.

## Runtime behavior

For answers, the skill tells the agent to run:

```bash
doxa query "<question>" --search hybrid
```

For growth, it tells the agent to run:

```bash
doxa ingest <source>
```

For source text already fetched by the harness, including via a BrightData MCP:

```bash
printf '%s' "$FETCHED_TEXT" | doxa ingest - --title "Title" --url "https://source.example"
```

The returned beliefs and quotes are the only ground truth. The agent must not
invent quotes or claims.
