"""Provider that delegates mining to the user's Codex CLI."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess  # nosec B404
import tempfile
from typing import Any

from doxa.schema import DoxaError

_CODEX_BYPASS_FLAG = "--dangerously-" + "bypass-approvals-and-sandbox"


class CodexCliProvider:
    """Run ``codex exec`` headlessly and read the JSON result it writes."""

    def __init__(self, config: dict[str, Any]):
        provider_config = (config.get("providers") or {}).get("codex-cli", {})
        self.binary = str(provider_config.get("binary") or "codex")
        self.flags = [str(flag) for flag in provider_config.get("flags", ["exec"])]
        if provider_config.get("unsafe_bypass") and _CODEX_BYPASS_FLAG not in self.flags:
            self.flags.append(_CODEX_BYPASS_FLAG)
        self.output_flag = str(provider_config.get("output_flag") or "-o")
        self.timeout = int(provider_config.get("timeout", 300))
        if shutil.which(self.binary) is None:
            raise DoxaError(
                "codex-cli provider needs the Codex CLI on PATH. Install Codex CLI or set providers.codex-cli.binary."
            )

    def complete(self, system: str, user: str) -> str:
        prompt = system + "\n\n" + user
        with tempfile.NamedTemporaryFile(prefix="doxa-codex-", suffix=".json", delete=False) as handle:
            output_path = Path(handle.name)
        try:
            cmd = [self.binary, *self.flags, self.output_flag, str(output_path), "-"]
            try:
                completed = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=self.timeout,
                )  # nosec B603 - configured argv-only provider CLI invocation.
            except subprocess.TimeoutExpired:
                raise DoxaError(f"Codex CLI provider timed out after {self.timeout}s.") from None
            if completed.returncode != 0:
                raise DoxaError(
                    "Codex CLI provider failed. Check your Codex auth or configure providers.codex-cli.flags. "
                    f"stderr: {completed.stderr.strip()}"
                )
            if output_path.exists() and output_path.read_text(encoding="utf-8").strip():
                return output_path.read_text(encoding="utf-8")
            if completed.stdout.strip():
                return completed.stdout
            raise DoxaError("Codex CLI provider returned no output. Configure an output flag or use a different provider.")
        finally:
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass
