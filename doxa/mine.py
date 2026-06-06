"""Belief mining with provider-independent verbatim checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import json
import re
import uuid

from .lens import build_extraction_prompt
from .providers import get_provider
from .schema import Belief, DoxaError, Quote, SourceRecord, quote_is_verbatim


@dataclass(slots=True)
class MiningResult:
    beliefs: list[Belief]
    quotes: list[Quote]
    dropped_quotes: list[dict[str, str]] = field(default_factory=list)
    dropped_beliefs: list[str] = field(default_factory=list)


def chunk_text(text: str, *, max_chars: int = 12000, overlap: int = 600) -> list[str]:
    """Split text into overlapping chunks without external tokenizers."""

    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        if end < len(cleaned):
            boundary = cleaned.rfind("\n\n", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        chunks.append(cleaned[start:end].strip())
        if end == len(cleaned):
            break
        start = max(end - overlap, 0)
    return chunks


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_provider_json(text: str) -> dict[str, Any]:
    """Parse strict JSON, including common CLI wrappers around model output."""

    cleaned = _strip_code_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise DoxaError("Provider did not return parseable JSON.")
        parsed = json.loads(match.group(0))
    if isinstance(parsed, dict) and "beliefs" in parsed and "quotes" in parsed:
        return parsed
    for key in ("result", "output", "text", "content"):
        value = parsed.get(key) if isinstance(parsed, dict) else None
        if isinstance(value, str):
            return parse_provider_json(value)
        if isinstance(value, list):
            joined = "\n".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in value)
            return parse_provider_json(joined)
    raise DoxaError('Provider JSON must contain top-level "beliefs" and "quotes" keys.')


def _stable_id(prefix: str, source_id: str, chunk_index: int, local_id: str) -> str:
    raw = f"{prefix}:{source_id}:{chunk_index}:{local_id}"
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, raw).hex[:12]}"


def mine_source(
    source: SourceRecord,
    config: dict[str, Any],
    *,
    progress: Callable[[int, int], None] | None = None,
) -> MiningResult:
    """Mine a source with the configured provider and verify every quote.

    ``progress``, if given, is called with (chunk_index, total_chunks) before each
    chunk is mined so callers can show a live progress line during a long ingest.
    """

    provider = get_provider(config)
    all_beliefs: list[Belief] = []
    all_quotes: list[Quote] = []
    dropped_quotes: list[dict[str, str]] = []
    source_meta = source.ref.to_dict()
    chunks = chunk_text(source.text)
    for chunk_index, chunk in enumerate(chunks, start=1):
        if progress is not None:
            progress(chunk_index, len(chunks))
        system, user = build_extraction_prompt(config, source_meta, chunk)
        raw = parse_provider_json(provider.complete(system, user))
        local_beliefs = [Belief.from_dict({**item, "source": item.get("source") or source_meta}) for item in raw.get("beliefs", [])]
        local_quotes = [Quote.from_dict({**item, "source": item.get("source") or source_meta}) for item in raw.get("quotes", [])]
        for belief in local_beliefs:
            if not belief.source.id:
                belief.source.id = source.id
        for quote in local_quotes:
            if not quote.source.id:
                quote.source.id = source.id

        id_map = {belief.id: _stable_id("b", source.id, chunk_index, belief.id) for belief in local_beliefs}
        for belief in local_beliefs:
            belief.id = id_map[belief.id]
        valid_quotes: list[Quote] = []
        for quote in local_quotes:
            if not quote_is_verbatim(quote.quote, source.text):
                dropped_quotes.append({"id": quote.id, "quote": quote.quote, "reason": "not found verbatim in source"})
                continue
            quote.id = _stable_id("q", source.id, chunk_index, quote.id)
            quote.belief_ids = [id_map[belief_id] for belief_id in quote.belief_ids if belief_id in id_map]
            if quote.belief_ids:
                valid_quotes.append(quote)
            else:
                dropped_quotes.append({"id": quote.id, "quote": quote.quote, "reason": "no valid belief link"})
        anchored_ids = {belief_id for quote in valid_quotes for belief_id in quote.belief_ids}
        all_beliefs.extend([belief for belief in local_beliefs if belief.id in anchored_ids])
        all_quotes.extend(valid_quotes)
    # Overlapping chunks can restate the same belief; collapse cross-chunk duplicates
    # (matched by normalized text) and repoint their quotes to the canonical belief id.
    canonical: dict[str, str] = {}
    remap: dict[str, str] = {}
    deduped: list[Belief] = []
    for belief in all_beliefs:
        key = " ".join(belief.belief.lower().split())
        if key in canonical:
            remap[belief.id] = canonical[key]
        else:
            canonical[key] = belief.id
            deduped.append(belief)
    if remap:
        for quote in all_quotes:
            quote.belief_ids = [remap.get(bid, bid) for bid in quote.belief_ids]
        all_beliefs = deduped

    dropped_beliefs = sorted({belief.id for belief in all_beliefs} - {bid for quote in all_quotes for bid in quote.belief_ids})
    return MiningResult(
        beliefs=[belief for belief in all_beliefs if belief.id not in dropped_beliefs],
        quotes=all_quotes,
        dropped_quotes=dropped_quotes,
        dropped_beliefs=dropped_beliefs,
    )

