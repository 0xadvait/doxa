"""Terminal banner rendering.

The bundled banner (``doxa/_assets/banner.txt``) is a side-by-side lockup: a
braille oracle orb on the left and the half-block DOXA wordmark on the right,
inside a dashed frame. Coloring is done per character *class* so the orb and the
wordmark can take different colors even when they share a line. Colorizing only
wraps runs in ANSI escapes -- it never changes the underlying characters, so
stripping the escapes always yields the original banner text.
"""

from __future__ import annotations

import os
from typing import TextIO

from .resources import banner_text


RESET = "\033[0m"
FRAME = "\033[38;5;240m"     # dim grey dashed border
TITLE = "\033[1;38;5;231m"   # bright white DOXA wordmark
ORACLE = "\033[38;5;81m"     # cyan wireframe orb
MUTED = "\033[38;5;245m"     # anything else

_BLOCKS = "█▀▄▌▐░▒▓▙▟▛▜▖▗▘▝"
_FRAME_CHARS = "+-|"


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


def _char_color(ch: str) -> str:
    code = ord(ch)
    if 0x2800 <= code <= 0x28FF:   # braille -> the orb
        return ORACLE
    if ch in _BLOCKS:             # half-block -> the wordmark
        return TITLE
    if ch in _FRAME_CHARS:        # dashed frame
        return FRAME
    return MUTED


def colorize_banner(text: str) -> str:
    rendered: list[str] = []
    for line in text.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        out = ""
        i = 0
        n = len(body)
        while i < n:
            ch = body[i]
            if ch == " ":            # leave plain spaces uncolored
                out += " "
                i += 1
                continue
            color = _char_color(ch)
            j = i
            run = ""
            while j < n and body[j] != " " and _char_color(body[j]) == color:
                run += body[j]
                j += 1
            out += f"{color}{run}{RESET}"
            i = j
        rendered.append(out + newline)
    return "".join(rendered)


def render_banner(*, color: str = "auto", stream: TextIO) -> str:
    text = banner_text()
    if should_use_color(color, stream):
        return colorize_banner(text)
    return text
