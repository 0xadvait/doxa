"""OpenAI-compatible Chat Completions provider."""

from __future__ import annotations

import os
from typing import Any

from doxa.schema import DoxaError


class OpenAICompatibleProvider:
    """Use OpenAI, Fireworks, vLLM, llama.cpp, or another Chat Completions server."""

    def __init__(self, config: dict[str, Any], *, provider_name: str = "openai-compatible"):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise DoxaError("OpenAI-compatible providers require the openai extra: install doxa[openai].") from exc

        providers = config.get("providers") or {}
        provider_config = providers.get(provider_name) or providers.get("openai-compatible") or providers.get("openai") or {}
        llm_config = config.get("llm") or {}
        self.model = str(llm_config.get("model") or provider_config.get("model") or "")
        if not self.model:
            raise DoxaError("Set llm.model or providers.openai-compatible.model before using this provider.")
        api_key_env = str(provider_config.get("api_key_env") or "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise DoxaError(f"Set {api_key_env} before using the {provider_name} provider.")
        base_url = str(provider_config.get("base_url") or "").strip() or None
        self.temperature = float(llm_config.get("temperature", 0))
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise DoxaError("OpenAI-compatible provider returned an empty message.")
        return content

