from __future__ import annotations

from doxa.answer import clean_human_prose, render_terminal_answer
from doxa.schema import Belief, Quote, RetrievalResult, SourceRef


def _result(*, belief_text: str, quote_text: str) -> RetrievalResult:
    source = SourceRef(title="Source", author="Author", date="2026")
    return RetrievalResult(
        belief=Belief(
            id="b1",
            belief=belief_text,
            reasoning="",
            stance="supports",
            conviction=0.8,
            tags=[],
            source=source,
        ),
        quotes=[
            Quote(
                id="q1",
                quote=quote_text,
                speaker="",
                source=source,
                context="",
                tags=[],
                belief_ids=["b1"],
            )
        ],
        score=1.0,
    )


def test_render_terminal_answer_preserves_quote_bytes() -> None:
    quote = 'Keep  two spaces, "inner quotes",\nline breaks, and\ttabs intact.'
    rendered = render_terminal_answer(
        "how exact is the evidence?",
        [_result(belief_text="The quote must remain exact", quote_text=quote)],
    )

    assert quote.encode("utf-8") in rendered.encode("utf-8")


def test_render_terminal_answer_cleans_aiish_non_quote_prose() -> None:
    belief = (
        "As an AI language model, based on the provided text, "
        "it is important to note that people should trust direct experience"
    )
    rendered = render_terminal_answer(
        "what should people trust?",
        [_result(belief_text=belief, quote_text="Trust thyself: every heart vibrates to that iron string.")],
    )

    assert belief not in rendered
    assert "As an AI" not in rendered
    assert "provided text" not in rendered
    assert "important to note" not in rendered
    assert "People should trust direct experience." in rendered


def test_clean_human_prose_rewrites_aiish_passage_language() -> None:
    assert clean_human_prose("This passage highlights that courage matters") == "The source says that courage matters."


def test_render_terminal_answer_omits_unquoted_beliefs() -> None:
    source = SourceRef(title="Source")
    result = RetrievalResult(
        belief=Belief(
            id="b1",
            belief="A claim without a returned quote should not be surfaced in answer mode.",
            reasoning="",
            stance="supports",
            conviction=0.8,
            tags=[],
            source=source,
        ),
        quotes=[],
        score=1.0,
    )

    rendered = render_terminal_answer("what is true?", [result])

    assert "claim without a returned quote" not in rendered
    assert "don't have enough grounded evidence" in rendered
