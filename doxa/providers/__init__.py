"""LLM provider registry."""

from __future__ import annotations

from typing import Any, Protocol

from doxa.schema import DoxaError


class Provider(Protocol):
    """Minimal provider contract used by the miner."""

    def complete(self, system: str, user: str) -> str:
        """Return model text. Mining expects strict JSON in the returned text."""


def get_provider(config: dict[str, Any]) -> Provider:
    """Construct the configured provider."""

    provider_name = str((config.get("llm") or {}).get("provider") or "codex-cli")
    if provider_name == "codex-cli":
        from .codex_cli import CodexCliProvider

        return CodexCliProvider(config)
    if provider_name == "claude-cli":
        from .claude_cli import ClaudeCliProvider

        return ClaudeCliProvider(config)
    if provider_name in {"openai", "openai-compatible", "fireworks"}:
        from .openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(config, provider_name=provider_name)
    if provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(config)
    raise DoxaError(
        f"Unknown llm.provider '{provider_name}'. Use codex-cli, claude-cli, openai-compatible, openai, or anthropic."
    )

