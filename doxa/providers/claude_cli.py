"""Provider that delegates mining to Claude Code CLI."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from doxa.schema import DoxaError


class ClaudeCliProvider:
    """Run Claude Code headlessly and parse its JSON output."""

    def __init__(self, config: dict[str, Any]):
        provider_config = (config.get("providers") or {}).get("claude-cli", {})
        self.binary = str(provider_config.get("binary") or "claude")
        self.flags = [str(flag) for flag in provider_config.get("flags", ["-p", "{prompt}", "--output-format", "json"])]
        if shutil.which(self.binary) is None:
            raise DoxaError(
                "claude-cli provider needs the Claude Code CLI on PATH. Install Claude Code or set providers.claude-cli.binary."
            )

    def complete(self, system: str, user: str) -> str:
        prompt = system + "\n\n" + user
        cmd = [self.binary, *[flag.replace("{prompt}", prompt) for flag in self.flags]]
        completed = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise DoxaError(
                "Claude CLI provider failed. Check your Claude Code auth or configure providers.claude-cli.flags. "
                f"stderr: {completed.stderr.strip()}"
            )
        if not completed.stdout.strip():
            raise DoxaError("Claude CLI provider returned no output.")
        return completed.stdout

