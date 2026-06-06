"""Lens prompts for belief mining."""

from __future__ import annotations

from typing import Any

from .domains import domain_prompt_lines


DEFAULT_LENS_NAME = "beliefs"
DEFAULT_LENS_QUESTION = "What beliefs does this source express?"
DEFAULT_STANCES = ["supports", "questions", "rejects", "complicates"]


SYSTEM_PROMPT = """You are doxa, a careful belief-mining engine.
Extract only beliefs grounded in exact quotes from the provided source.
Return strict JSON only. Do not invent quotes, sources, or claims."""


def _list_items(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item).strip()]
    return []


def normalize_lens(raw_lens: Any) -> dict[str, Any]:
    """Return a dict-shaped lens, accepting shorthand string lenses."""

    if isinstance(raw_lens, str):
        return {
            "name": DEFAULT_LENS_NAME,
            "description": raw_lens.strip(),
            "question": DEFAULT_LENS_QUESTION,
            "stances": list(DEFAULT_STANCES),
            "tags": [],
        }
    if isinstance(raw_lens, dict):
        return raw_lens
    return {}


def lens_text(config: dict[str, Any]) -> str:
    lens = normalize_lens(config.get("lens"))
    stances = ", ".join(_list_items(lens.get("stances")))
    tags = ", ".join(_list_items(lens.get("tags"))) or "none pre-specified"
    return "\n".join(
        [
            f"Lens name: {lens.get('name', DEFAULT_LENS_NAME)}",
            f"Lens description: {lens.get('description', '')}",
            f"Guiding question: {lens.get('question', DEFAULT_LENS_QUESTION)}",
            f"Allowed stances: {stances or ', '.join(DEFAULT_STANCES)}",
            f"Suggested tags: {tags}",
            *domain_prompt_lines(config),
        ]
    )


def build_extraction_prompt(config: dict[str, Any], source_meta: dict[str, str], chunk_text: str) -> tuple[str, str]:
    """Build the system and user prompts for strict JSON extraction."""

    source_block = "\n".join(
        [
            f"Title: {source_meta.get('title', 'Untitled source')}",
            f"Author: {source_meta.get('author', '')}",
            f"Date: {source_meta.get('date', '')}",
            f"URL: {source_meta.get('url', '')}",
        ]
    )
    user = f"""Mine this source chunk using the lens below.

{lens_text(config)}

Source metadata:
{source_block}

Rules:
- Extract EVERY distinct belief this lens surfaces in the source text. There is no
  target number -- never cap the list to a round count and never pad it. Scale to the
  source: a rich passage yields many beliefs, a thin one few. Mine the whole chunk and
  omit nothing that fits the lens; do not stop early to keep the output short.
- Likewise mine every verbatim quote that grounds a belief -- as many as the text supports.
- Every quote.quote must be copied verbatim from Source text.
- Each belief must be linked by at least one quote.belief_ids entry.
- Prefer concise beliefs that each state one stance, not a summary paragraph -- but split
  a passage into multiple beliefs rather than dropping any; one belief per distinct claim.
- Use domain:<slug> tags only when the source text clearly supports that domain classification.
- conviction is a number from 0 to 1 based only on how directly the quote supports the belief.
- Return strict JSON with top-level keys "beliefs" and "quotes".
- Use this shape:
{{
  "beliefs": [
    {{
      "id": "b1",
      "belief": "...",
      "reasoning": "...",
      "stance": "supports",
      "conviction": 0.82,
      "tags": ["..."],
      "source": {{"title": "...", "author": "...", "date": "...", "url": "..."}}
    }}
  ],
  "quotes": [
    {{
      "id": "q1",
      "quote": "exact source substring",
      "speaker": "...",
      "source": {{"title": "...", "author": "...", "date": "...", "url": "..."}},
      "context": "short surrounding context",
      "tags": ["..."],
      "belief_ids": ["b1"]
    }}
  ]
}}

Source text:
\"\"\"
{chunk_text}
\"\"\"
"""
    return SYSTEM_PROMPT, user
