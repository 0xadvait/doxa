"""Local answer rendering for retrieved, quote-grounded beliefs."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .schema import Quote, RetrievalResult, SourceRef


_AI_PROSE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^as an ai(?: language model)?,?\s*(?:i (?:think|believe|would say) that\s*)?", re.IGNORECASE),
        "",
    ),
    (re.compile(r"^i (?:think|believe|would say) that\s+", re.IGNORECASE), ""),
    (
        re.compile(r"^based on (?:the|this) (?:provided )?(?:text|source|passage),?\s*", re.IGNORECASE),
        "",
    ),
    (re.compile(r"^(?:overall|in conclusion|to summarize),?\s*", re.IGNORECASE), ""),
    (re.compile(r"\bit is important to note that\s+", re.IGNORECASE), ""),
    (
        re.compile(
            r"\bthis (?:quote|passage|text) (?:suggests|indicates|highlights|underscores) that\b",
            re.IGNORECASE,
        ),
        "the source says that",
    ),
)


def clean_human_prose(text: str) -> str:
    """Clean generated-looking boilerplate from non-verbatim prose."""

    cleaned = re.sub(r"\s+", " ", text or "").strip(" -*")
    for pattern, replacement in _AI_PROSE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;:-")
    if not cleaned:
        return ""
    if cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _source_label(source: SourceRef) -> str:
    parts = [source.title, source.author, source.date]
    return " / ".join(part for part in parts if part)


def _quote_lines(quote: Quote) -> list[str]:
    speaker = f"{quote.speaker}: " if quote.speaker else ""
    lines = [f'   Quote: {speaker}"{quote.quote}"']
    source = _source_label(quote.source)
    if source:
        lines.append(f"   Source: {source}")
    return lines


def _claim_text(result: RetrievalResult) -> str:
    return (
        clean_human_prose(result.belief.belief)
        or clean_human_prose(result.belief.reasoning)
        or "The returned belief is grounded by the quoted evidence."
    )


def render_terminal_answer(query: str, results: Sequence[RetrievalResult]) -> str:
    """Render a deterministic terminal answer without changing quote strings."""

    del query
    grounded = [result for result in results if result.quotes]
    if not grounded:
        return "I don't have enough grounded evidence in the belief base to answer that."

    if len(grounded) == 1:
        result = grounded[0]
        lines = ["The belief base points to this:", "", _claim_text(result), "", "Evidence:"]
        for quote in result.quotes:
            lines.extend(_quote_lines(quote))
        return "\n".join(lines)

    lines = ["The belief base points to these grounded takeaways:"]
    for index, result in enumerate(grounded, start=1):
        lines.extend(["", f"{index}. {_claim_text(result)}"])
        for quote in result.quotes:
            lines.extend(_quote_lines(quote))
    return "\n".join(lines)
