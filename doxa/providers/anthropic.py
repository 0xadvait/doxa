"""Anthropic API provider."""

from __future__ import annotations

import os
from typing import Any

from doxa.schema import DoxaError


class AnthropicProvider:
    """Use Claude through the Anthropic API."""

    def __init__(self, config: dict[str, Any]):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise DoxaError("Anthropic provider requires the anthropic extra: install doxa[anthropic].") from exc
        provider_config = (config.get("providers") or {}).get("anthropic", {})
        llm_config = config.get("llm") or {}
        api_key_env = str(provider_config.get("api_key_env") or "ANTHROPIC_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise DoxaError(f"Set {api_key_env} before using the anthropic provider.")
        self.model = str(llm_config.get("model") or provider_config.get("model") or "claude-3-5-sonnet-latest")
        self.temperature = float(llm_config.get("temperature", 0))
        self.client = Anthropic(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        text = "\n".join(parts).strip()
        if not text:
            raise DoxaError("Anthropic provider returned no text content.")
        return text

