#!/usr/bin/env python3
"""Regenerate doxa/_assets/banner.txt from the source art in assets/.

The terminal banner is a side-by-side lockup: the oracle orb (braille) on the
left, the DOXA wordmark (half-block, circuit-etched) on the right, in a dashed
frame. The colorful PCB / cyber-orb PNGs in assets/ are the source of truth;
this tool downsamples them to the fixed-width text artifact the package ships.

Requires Pillow (dev-only). Run:  python3 tools/build_banner.py
"""
from __future__ import annotations

import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ROOT / "doxa" / "_assets" / "banner.txt"

# --- layout knobs ---
TITLE_SRC = "doxa_etched.png"   # solid white DOXA with circuit traces etched in
ORB_SRC = "mascot_orb.png"      # wireframe oracle globe + all-seeing eye
TITLE_COLS = 46
TITLE_THRESH = 85  # lower than 100 so etched traces don't punch a gap in the O
ORB_COLS = 20
ORB_THRESH = 74
GAP = 5                         # spaces between orb and wordmark
INNER = 78                      # width between the | bars

_DOT = [(0,0,0x01),(0,1,0x02),(0,2,0x04),(0,3,0x40),
        (1,0,0x08),(1,1,0x10),(1,2,0x20),(1,3,0x80)]


def _crop(img: Image.Image, floor: int = 28) -> Image.Image:
    g = img.convert("L")
    bb = g.point(lambda p: 255 if p > floor else 0).getbbox()
    if bb:
        left, top, right, bottom = bb
        m = 2
        img = img.crop((max(0, left - m), max(0, top - m),
                        min(img.width, right + m), min(img.height, bottom + m)))
    return img


def to_braille(path: pathlib.Path, cols: int, thresh: int) -> list[str]:
    img = _crop(Image.open(path).convert("L"))
    Wc, Hc = img.size
    dots_w = cols * 2
    rows = max(1, round(dots_w * Hc / Wc / 4))
    img = img.resize((dots_w, rows * 4), Image.LANCZOS)
    px = img.load()
    W, H = img.size
    out = []
    for by in range(0, H, 4):
        line = ""
        for bx in range(0, W, 2):
            v = 0
            for dx, dy, bit in _DOT:
                x, y = bx + dx, by + dy
                if x < W and y < H and px[x, y] > thresh:
                    v |= bit
            line += chr(0x2800 + v)
        out.append(line)
    return [r.ljust(cols) for r in out]


def to_halfblock(path: pathlib.Path, cols: int, thresh: int) -> list[str]:
    img = _crop(Image.open(path).convert("L"))
    Wc, Hc = img.size
    rows = max(1, round(cols * Hc / Wc / 2))
    img = img.resize((cols, rows * 2), Image.LANCZOS)
    px = img.load()
    out = []
    for ry in range(rows):
        line = ""
        for x in range(cols):
            top = px[x, ry * 2] > thresh
            bot = px[x, ry * 2 + 1] > thresh
            line += "█" if top and bot else "▀" if top else "▄" if bot else " "
        out.append(line)
    return [r.ljust(cols) for r in out]


def lockup() -> list[str]:
    title = to_halfblock(ASSETS / TITLE_SRC, TITLE_COLS, TITLE_THRESH)
    orb = to_braille(ASSETS / ORB_SRC, ORB_COLS, ORB_THRESH)
    h = max(len(title), len(orb))
    # vertically center each column within h
    def pad(col, w):
        top = (h - len(col)) // 2
        return [" " * w] * top + col + [" " * w] * (h - len(col) - top)
    title = pad(title, TITLE_COLS)
    orb = pad(orb, ORB_COLS)

    block_w = ORB_COLS + GAP + TITLE_COLS
    left = (INNER - block_w) // 2
    rows = []
    for o, t in zip(orb, title):
        body = " " * left + o + " " * GAP + t
        rows.append(body.ljust(INNER))
    return rows


def frame(rows: list[str]) -> str:
    dash = "".join("-" if i % 2 == 0 else " " for i in range(INNER))
    top = "+" + dash + "+"
    blank = "|" + " " * INNER + "|"
    body = [top, blank]
    for r in rows:
        body.append("|" + r[:INNER].ljust(INNER) + "|")
    body += [blank, top]
    return "\n".join(body) + "\n"


def main() -> None:
    text = frame(lockup())
    OUT.write_text(text, encoding="utf-8")
    widths = {len(line) for line in text.splitlines()}
    print(f"wrote {OUT} ({len(text.splitlines())} lines, widths={sorted(widths)})")


if __name__ == "__main__":
    main()
