"""Core schemas and validation helpers for doxa."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


class DoxaError(RuntimeError):
    """Base exception for actionable doxa errors."""


def normalize_ws(text: str) -> str:
    """Collapse whitespace for quote verification across line wrapping."""

    return re.sub(r"\s+", " ", text or "").strip()


def _parse_conviction(raw: Any) -> float:
    """Parse numeric or legacy label convictions into a 0..1 confidence score."""

    if isinstance(raw, str):
        label = raw.strip().lower()
        legacy_labels = {
            "weak": 0.25,
            "low": 0.25,
            "exploring": 0.45,
            "medium": 0.55,
            "moderate": 0.55,
            "strong": 0.85,
            "high": 0.85,
            "certain": 0.95,
        }
        if label in legacy_labels:
            return legacy_labels[label]
    try:
        conviction = float(raw)
    except (TypeError, ValueError) as exc:
        raise DoxaError("Belief.conviction must be a number or known label (weak, exploring, medium, strong).") from exc
    if conviction < 0:
        return 0.0
    if conviction > 1:
        return 1.0
    return conviction


def quote_is_verbatim(quote: str, source_text: str) -> bool:
    """Return true when ``quote`` occurs in ``source_text`` after whitespace normalization."""

    normalized_quote = normalize_ws(quote)
    if not normalized_quote:
        return False
    return normalized_quote in normalize_ws(source_text)


@dataclass(slots=True)
class SourceRef:
    """Public metadata for a source."""

    title: str = "Untitled source"
    author: str = ""
    date: str = ""
    url: str = ""
    id: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "SourceRef":
        raw = raw or {}
        title = str(raw.get("title") or "Untitled source").strip()
        return cls(
            title=title,
            author=str(raw.get("author") or "").strip(),
            date=str(raw.get("date") or "").strip(),
            url=str(raw.get("url") or "").strip(),
            id=str(raw.get("id") or raw.get("source_id") or "").strip(),
        )

    def to_dict(self) -> dict[str, str]:
        data = {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "url": self.url,
        }
        if self.id:
            data["id"] = self.id
        return data


@dataclass(slots=True)
class Belief:
    """A distilled stance, always intended to be backed by linked verbatim quotes."""

    id: str
    belief: str
    reasoning: str
    stance: str
    conviction: float
    tags: list[str] = field(default_factory=list)
    source: SourceRef = field(default_factory=SourceRef)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Belief":
        missing = [key for key in ("id", "belief", "reasoning", "stance", "conviction") if key not in raw]
        if missing:
            raise DoxaError(f"Belief is missing required field(s): {', '.join(missing)}")
        tags = raw.get("tags") or []
        if not isinstance(tags, list):
            raise DoxaError("Belief.tags must be a list")
        conviction = _parse_conviction(raw["conviction"])
        return cls(
            id=str(raw["id"]).strip(),
            belief=str(raw["belief"]).strip(),
            reasoning=str(raw["reasoning"]).strip(),
            stance=str(raw["stance"]).strip(),
            conviction=conviction,
            tags=[str(tag).strip() for tag in tags if str(tag).strip()],
            source=SourceRef.from_dict(raw.get("source")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "belief": self.belief,
            "reasoning": self.reasoning,
            "stance": self.stance,
            "conviction": self.conviction,
            "tags": list(self.tags),
            "source": self.source.to_dict(),
        }


@dataclass(slots=True)
class Quote:
    """A verbatim source quote linked to one or more beliefs."""

    id: str
    quote: str
    speaker: str
    source: SourceRef
    context: str
    tags: list[str] = field(default_factory=list)
    belief_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Quote":
        missing = [key for key in ("id", "quote", "speaker", "source", "context", "belief_ids") if key not in raw]
        if missing:
            raise DoxaError(f"Quote is missing required field(s): {', '.join(missing)}")
        tags = raw.get("tags") or []
        belief_ids = raw.get("belief_ids") or []
        if not isinstance(tags, list):
            raise DoxaError("Quote.tags must be a list")
        if not isinstance(belief_ids, list):
            raise DoxaError("Quote.belief_ids must be a list")
        return cls(
            id=str(raw["id"]).strip(),
            quote=str(raw["quote"]).strip(),
            speaker=str(raw["speaker"]).strip(),
            source=SourceRef.from_dict(raw.get("source")),
            context=str(raw["context"]).strip(),
            tags=[str(tag).strip() for tag in tags if str(tag).strip()],
            belief_ids=[str(bid).strip() for bid in belief_ids if str(bid).strip()],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "quote": self.quote,
            "speaker": self.speaker,
            "source": self.source.to_dict(),
            "context": self.context,
            "tags": list(self.tags),
            "belief_ids": list(self.belief_ids),
        }


@dataclass(slots=True)
class SourceRecord:
    """Stored source text used for re-checking quote faithfulness."""

    id: str
    title: str
    author: str
    date: str
    url: str
    path: str
    text: str

    @property
    def ref(self) -> SourceRef:
        return SourceRef(title=self.title, author=self.author, date=self.date, url=self.url, id=self.id)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceRecord":
        return cls(
            id=str(raw.get("id") or raw.get("title") or "source").strip(),
            title=str(raw.get("title") or "Untitled source").strip(),
            author=str(raw.get("author") or "").strip(),
            date=str(raw.get("date") or "").strip(),
            url=str(raw.get("url") or "").strip(),
            path=str(raw.get("path") or "").strip(),
            text=str(raw.get("text") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "url": self.url,
            "path": self.path,
            "text": self.text,
        }


@dataclass(slots=True)
class RetrievalResult:
    """A belief plus the verbatim quotes that ground it."""

    belief: Belief
    quotes: list[Quote]
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "belief": self.belief.to_dict(),
            "quotes": [quote.to_dict() for quote in self.quotes],
        }
