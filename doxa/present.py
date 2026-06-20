"""Presentation profiles: optional voices for composing a grounded answer.

doxa retrieves evidence; the agent reading it composes the prose answer. A
presentation profile is an optional *composition directive* the CLI can emit
alongside that evidence. It changes the voice and shape of the answer, never
the grounding: the retrieved beliefs and verbatim quotes remain the only
evidence, and nothing may be invented.

The default profile is ``plain`` (no directive: current behavior). The flagship
optional profile is ``hawking``, distilled from how Stephen Hawking presented
evidence in the first two chapters of *A Brief History of Time* -- framing hard
ideas as an ancient human quest, staging a procession of minds, saying the
largest thing in the plainest sentence, and turning each answer into a question
about what we can know.

Short Hawking phrases appear as style exemplars (illustration and commentary,
attributed to *A Brief History of Time*); the book itself is not bundled.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import DoxaError


DEFAULT_PROFILE = "plain"

_HAWKING_SOURCE = "Stephen Hawking, A Brief History of Time"


@dataclass(frozen=True, slots=True)
class Move:
    """A single compositional move: how to do it, with a short exemplar."""

    name: str
    directive: str
    exemplar: str = ""
    exemplar_source: str = ""


@dataclass(frozen=True, slots=True)
class PresentationProfile:
    """An optional voice for composing the final answer from retrieved evidence."""

    name: str
    title: str
    summary: str
    when_to_use: str = ""
    grounding_note: str = ""
    arc: tuple[str, ...] = ()
    moves: tuple[Move, ...] = ()
    constraints: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()

    def is_plain(self) -> bool:
        """A plain profile carries no directive and leaves output unchanged."""

        return not (self.arc or self.moves or self.constraints)

    def render_directive(self) -> str:
        """Render the composition directive an agent reads before writing.

        Returns an empty string for plain profiles so callers can treat
        "no directive" uniformly.
        """

        if self.is_plain():
            return ""

        lines: list[str] = []
        lines.append(f"=== doxa presentation directive: {self.name} ===")
        lines.append(self.title)
        lines.append("")
        lines.append(self.summary)
        if self.when_to_use:
            lines.append("")
            lines.append(f"When to use: {self.when_to_use}")
        if self.grounding_note:
            lines.append("")
            lines.append(f"Grounding (inviolable): {self.grounding_note}")
        if self.arc:
            lines.append("")
            lines.append("Arc -- shape the answer in these beats:")
            for index, beat in enumerate(self.arc, start=1):
                lines.append(f"  {index}. {beat}")
        if self.moves:
            lines.append("")
            lines.append("Moves -- techniques, each with a short exemplar:")
            for move in self.moves:
                lines.append(f"  - {move.name}: {move.directive}")
                if move.exemplar:
                    source = move.exemplar_source or _HAWKING_SOURCE
                    lines.append(f'      e.g. "{move.exemplar}" ({source})')
        if self.constraints:
            lines.append("")
            lines.append("Constraints -- hold these while writing:")
            for item in self.constraints:
                lines.append(f"  - {item}")
        if self.avoid:
            lines.append("")
            lines.append("Avoid:")
            for item in self.avoid:
                lines.append(f"  - {item}")
        lines.append("=== end presentation directive ===")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """Machine-readable form for ``--json`` consumers."""

        return {
            "name": self.name,
            "title": self.title,
            "summary": self.summary,
            "when_to_use": self.when_to_use,
            "grounding_note": self.grounding_note,
            "arc": list(self.arc),
            "moves": [
                {
                    "name": move.name,
                    "directive": move.directive,
                    "exemplar": move.exemplar,
                    "exemplar_source": move.exemplar_source or (_HAWKING_SOURCE if move.exemplar else ""),
                }
                for move in self.moves
            ],
            "constraints": list(self.constraints),
            "avoid": list(self.avoid),
            "directive": self.render_directive(),
        }


PLAIN_PROFILE = PresentationProfile(
    name="plain",
    title="Plain",
    summary="No presentation directive. Return evidence as-is; the agent composes in its own voice.",
)


HAWKING_PROFILE = PresentationProfile(
    name="hawking",
    title="Hawking -- the answer as a human quest",
    summary=(
        "Present the answer the way Stephen Hawking presented physics in A Brief "
        "History of Time: start from an ancient question rather than the apparatus, "
        "let the evidence arrive as a procession of minds, say the largest thing in "
        "the plainest sentence, keep the genuine strangeness intact, and turn the "
        "answer into a question about what we can actually know."
    ),
    when_to_use=(
        "A reflective or big-question prompt where the reader should feel the stakes "
        "and the limits of the answer, not just receive a verdict. Skip it for quick "
        "factual lookups."
    ),
    grounding_note=(
        "This mode changes the voice, never the evidence. Every belief and quote you "
        "present must still come from doxa's retrieved records; invent nothing. "
        "Hawking's authority came from never overstating what was known -- honor that "
        "by keeping each claim inside its grounding and marking its conviction "
        "honestly."
    ),
    arc=(
        "Open on the question as an old human one -- wonder, not machinery.",
        "Let the evidence arrive as a procession of minds, each one changing the picture (the retrieved beliefs are your cast).",
        "State the present best picture in plain sentences, with the real strangeness left in.",
        "Mark honestly where knowledge ends -- what is tested, what is still provisional (use stance and conviction).",
        "Close on what the answer means for what we can know, and why the question is worth asking.",
    ),
    moves=(
        Move(
            name="Open on the old question",
            directive="Begin with the human question underneath the topic, not the technical setup. Give the science existential weight.",
            exemplar="Where did the universe come from, and where is it going?",
        ),
        Move(
            name="Stage a procession of minds",
            directive="Introduce the evidence as a sequence of thinkers who each revised the picture, so the reader watches thought climb.",
            exemplar="As long ago as 340 BC the Greek philosopher Aristotle ... was able to put forward two good arguments",
        ),
        Move(
            name="Anchor abstraction in a homely image",
            directive="Tie each abstract point to one concrete, everyday picture. Keep it simple and physical.",
            exemplar="But it's turtles all the way down!",
        ),
        Move(
            name="Say the largest thing plainly",
            directive="Deliver the biggest claim in a short, flat sentence. Let the idea carry the grandeur, not the wording.",
            exemplar="In other words, the universe is expanding.",
        ),
        Move(
            name="Keep the strangeness intact",
            directive="Simplify without pretending the idea is easy. Leave the vertigo in rather than flattening it into a comfortable falsehood.",
            exemplar="time had a beginning at the big bang, in the sense that earlier times simply would not be defined",
        ),
        Move(
            name="Make the answer epistemology",
            directive="Name what kind of claim this is and how far it can be trusted. Turn the answer toward the limits of knowing.",
            exemplar="Any physical theory is always provisional, in the sense that it is only a hypothesis: you can never prove it.",
        ),
        Move(
            name="Humility and audacity together",
            directive="Admit what is not known and still reach for the largest question. Hold both at once.",
            exemplar="We do not yet have such a theory ... but we do already know many of the properties that it must have.",
        ),
        Move(
            name="Close on the human stakes",
            directive="End on why the question matters to people, not on a tidy summary.",
            exemplar="Humanity's deepest desire for knowledge is justification enough for our continuing quest.",
        ),
    ),
    constraints=(
        "Prefer short, declarative sentences. Plainness makes the ideas feel larger.",
        "Keep genuine strangeness; never simplify a hard idea into something false.",
        "Use one concrete, everyday image per abstract point.",
        "Wit is dry and rare -- a parenthetical, not a performance (e.g. \"Only time (whatever that may be) will tell.\").",
        "Respect epistemic status: tested-by-reasoning is not the same as verified. Say which, and never present an untested number as established fact.",
        "Attribute every quote and the people behind the beliefs. Quotes are evidence, not decoration.",
    ),
    avoid=(
        "Purple or ornate prose -- grandeur comes from the concepts, not the adjectives.",
        "False certainty, or hedging everything into mush.",
        "Dumbing an idea down to the point of inaccuracy.",
        "Quotes that only decorate -- every quote must do evidentiary work.",
    ),
)


_PROFILES: dict[str, PresentationProfile] = {
    PLAIN_PROFILE.name: PLAIN_PROFILE,
    HAWKING_PROFILE.name: HAWKING_PROFILE,
}


def available_profiles() -> list[str]:
    """Return profile names, with ``plain`` first."""

    names = [PLAIN_PROFILE.name]
    names.extend(name for name in _PROFILES if name != PLAIN_PROFILE.name)
    return names


def get_profile(name: str | None) -> PresentationProfile:
    """Resolve a profile by name, defaulting to ``plain``.

    Raises DoxaError on an unknown name so the CLI can report a clean error.
    """

    key = (name or DEFAULT_PROFILE).strip().lower()
    profile = _PROFILES.get(key)
    if profile is None:
        choices = ", ".join(available_profiles())
        raise DoxaError(f"Unknown presentation profile '{name}'. Use one of: {choices}.")
    return profile


def render_directive(name: str | None) -> str:
    """Render the directive for a named profile (empty string for plain)."""

    return get_profile(name).render_directive()
