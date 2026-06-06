"""Starter packs -- install a curated, pre-built belief base so doxa is useful the
moment it's installed, instead of facing an empty base and "what do I ingest?".

A pack is three JSONL files (`beliefs.jsonl`, `quotes.jsonl`, `sources.jsonl`) plus a
`pack.json` manifest. The bundled registry (`_assets/packs/registry.json`) maps a pack
name to where its files live; `doxa packs install <name>` fetches and merges them into
your base (dedup by id). `doxa packs export` builds a pack from any base, filtered by
ingest tag -- it ships short verbatim quotes + source links but never full source text,
so a pack stays a citation index, not a corpus dump.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from .resources import read_text
from .schema import Belief, DoxaError, Quote, SourceRecord
from .store import JsonlStore

_REGISTRY = ("packs", "registry.json")
_USER_AGENT = "doxa-packs/0.1"


# ---- registry ---------------------------------------------------------------

def load_registry() -> list[dict[str, Any]]:
    try:
        data = json.loads(read_text(*_REGISTRY))
    except (DoxaError, json.JSONDecodeError):
        return []
    packs = data.get("packs", []) if isinstance(data, dict) else []
    return [p for p in packs if isinstance(p, dict) and p.get("name")]


def get_pack(name: str) -> dict[str, Any]:
    registry = load_registry()
    for pack in registry:
        if pack["name"] == name:
            return pack
    available = ", ".join(p["name"] for p in registry) or "(none)"
    raise DoxaError(f"unknown pack '{name}'. Available: {available}")


# ---- install ----------------------------------------------------------------

def _read_pack_lines(location: str, filename: str) -> list[str]:
    """Read one pack file from a local dir or an http(s) base. Returns [] if absent."""
    if location.startswith(("http://", "https://")):
        url = location.rstrip("/") + "/" + filename
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            raise DoxaError(f"could not fetch {url}: {exc}") from exc
    else:
        path = Path(location).expanduser() / filename
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


def resolve_location(name_or_location: str) -> tuple[str, dict[str, Any]]:
    """A registry name resolves to its download url + meta; a path/URL is used as-is."""
    candidate = Path(name_or_location).expanduser()
    if name_or_location.startswith(("http://", "https://")) or candidate.is_dir():
        return name_or_location, {}
    pack = get_pack(name_or_location)
    url = pack.get("url")
    if not url:
        raise DoxaError(f"pack '{name_or_location}' is not published yet (no download URL).")
    return url, pack


def install_pack(name_or_location: str, store: JsonlStore) -> dict[str, int]:
    """Fetch a pack and merge new records (by id) into the store."""
    location, _meta = resolve_location(name_or_location)
    new_beliefs = [Belief.from_dict(json.loads(line)) for line in _read_pack_lines(location, "beliefs.jsonl")]
    new_quotes = [Quote.from_dict(json.loads(line)) for line in _read_pack_lines(location, "quotes.jsonl")]
    new_sources = [SourceRecord.from_dict(json.loads(line)) for line in _read_pack_lines(location, "sources.jsonl")]
    if not new_beliefs:
        raise DoxaError(f"pack '{name_or_location}' contained no beliefs.")
    have_b = {b.id for b in store.beliefs()}
    have_q = {q.id for q in store.quotes()}
    have_s = {s.id for s in store.sources()}
    add_b = [b for b in new_beliefs if b.id not in have_b]
    add_q = [q for q in new_quotes if q.id not in have_q]
    add_s = [s for s in new_sources if s.id not in have_s]
    store.append(add_b, add_q, add_s)
    return {
        "beliefs": len(add_b),
        "quotes": len(add_q),
        "sources": len(add_s),
        "skipped": len(new_beliefs) - len(add_b),
    }


# ---- export -----------------------------------------------------------------

def _slug_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "source"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_pack(
    *,
    beliefs_path: str | Path,
    quotes_path: str | Path | None,
    ingests: list[str] | None,
    out_dir: str | Path,
    meta: dict[str, Any],
) -> dict[str, int]:
    """Build a pack from raw belief/quote JSONL.

    Filters beliefs by ingest tag (or keeps all), gathers their linked quotes, and
    derives source records as refs only (title/author/date/url, NO stored text). Writes
    beliefs.jsonl / quotes.jsonl / sources.jsonl / pack.json into out_dir.
    """
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    tagset = set(ingests) if ingests else None

    kept_beliefs: list[Belief] = []
    kept_ids: set[str] = set()
    for line in Path(beliefs_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        if tagset is not None and raw.get("ingest") not in tagset:
            continue
        belief = Belief.from_dict(raw)  # normalize to the public schema
        kept_beliefs.append(belief)
        kept_ids.add(belief.id)

    kept_quotes: list[Quote] = []
    if quotes_path and Path(quotes_path).is_file():
        for line in Path(quotes_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if any(bid in kept_ids for bid in (raw.get("belief_ids") or [])):
                kept_quotes.append(Quote.from_dict(raw))

    sources: dict[tuple[str, str], SourceRecord] = {}
    for obj in (*kept_beliefs, *kept_quotes):
        ref = obj.source
        if not ref.title:
            continue
        key = (ref.title, ref.url)
        if key not in sources:
            sid = (ref.id or _slug_id(ref.title)).strip()
            sources[key] = SourceRecord(id=sid, title=ref.title, author=ref.author,
                                        date=ref.date, url=ref.url, path="", text="")

    _write_jsonl(out / "beliefs.jsonl", [b.to_dict() for b in kept_beliefs])
    _write_jsonl(out / "quotes.jsonl", [q.to_dict() for q in kept_quotes])
    _write_jsonl(out / "sources.jsonl", [s.to_dict() for s in sources.values()])
    counts = {"beliefs": len(kept_beliefs), "quotes": len(kept_quotes), "sources": len(sources)}
    (out / "pack.json").write_text(json.dumps({**meta, **counts}, indent=2) + "\n", encoding="utf-8")
    return counts
