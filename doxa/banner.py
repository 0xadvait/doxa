"""Terminal banner rendering."""

from __future__ import annotations

import os
from typing import TextIO

from .resources import banner_text


RESET = "\033[0m"
BORDER = "\033[38;5;45m"
TITLE = "\033[1;38;5;220m"
MUTED = "\033[38;5;245m"
SIGNAL = "\033[38;5;81m"
VERDICT = "\033[1;38;5;197m"
ORACLE = "\033[38;5;141m"


def should_use_color(mode: str, stream: TextIO) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    if mode != "auto":
        raise ValueError(f"Unsupported banner color mode: {mode}")
    if os.environ.get("NO_COLOR"):
        return False
    force_color = os.environ.get("FORCE_COLOR")
    if force_color and force_color != "0":
        return True
    term = os.environ.get("TERM", "")
    return bool(getattr(stream, "isatty", lambda: False)()) and term.lower() != "dumb"


def colorize_banner(text: str) -> str:
    rendered: list[str] = []
    for index, line in enumerate(text.splitlines(keepends=True)):
        body = line[:-1] if line.endswith("\n") else line
        newline = "\n" if line.endswith("\n") else ""
        color = _line_color(index, body)
        rendered.append(f"{color}{body}{RESET}{newline}")
    return "".join(rendered)


def render_banner(*, color: str = "auto", stream: TextIO) -> str:
    text = banner_text()
    if should_use_color(color, stream):
        return colorize_banner(text)
    return text


def _line_color(index: int, line: str) -> str:
    if index == 0 or line.startswith("╚"):
        return BORDER
    if "NO QUOTE // NO CLAIM" in line:
        return VERDICT
    if index <= 6:
        return TITLE
    if "⣿" in line or "⠛" in line or "⢀" in line:
        return ORACLE
    if "evidence" in line or "belief ==" in line or "every answer" in line:
        return SIGNAL
    return MUTED
