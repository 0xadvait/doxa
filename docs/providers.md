# Providers

All providers implement:

```python
complete(system: str, user: str) -> str
```

The returned text is expected to contain strict JSON for mining.

## codex-cli

Default-friendly, no API key. Uses the user's existing Codex CLI auth.

```yaml
llm:
  provider: codex-cli
providers:
  codex-cli:
    binary: codex
    flags: [exec, --dangerously-bypass-approvals-and-sandbox]
    output_flag: -o
```

## claude-cli

No API key. Uses the user's existing Claude Code auth.

```yaml
llm:
  provider: claude-cli
providers:
  claude-cli:
    binary: claude
    flags: [-p, "{prompt}", --output-format, json]
```

## OpenAI and OpenAI-compatible

Install `doxa[openai]`.

```yaml
llm:
  provider: openai
  model: gpt-4.1-mini
providers:
  openai:
    api_key_env: OPENAI_API_KEY
```

Fireworks custom/open-weights example:

```yaml
llm:
  provider: openai-compatible
  model: accounts/fireworks/models/<slug>
providers:
  openai-compatible:
    base_url: https://api.fireworks.ai/inference/v1
    api_key_env: FIREWORKS_API_KEY
```

The same provider can point at vLLM, llama.cpp, or any Chat Completions-compatible
local server.

## Anthropic

Install `doxa[anthropic]`.

```yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-latest
providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
```

