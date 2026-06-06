from __future__ import annotations

import pytest

from doxa.stem import STOPWORDS, stem


# Final Porter (1980) outputs, verified equal to NLTK's original-mode PorterStemmer.
# (These are post-step-5 stems, not the step-1b intermediates shown in Porter's paper.)
PORTER_PAIRS = {
    "caresses": "caress", "ponies": "poni", "ties": "ti", "caress": "caress", "cats": "cat",
    "feed": "feed", "agreed": "agre", "plastered": "plaster", "bled": "bled",
    "motoring": "motor", "sing": "sing", "conflated": "conflat", "troubled": "troubl",
    "sized": "size", "hopping": "hop", "tanned": "tan", "falling": "fall", "hissing": "hiss",
    "fizzed": "fizz", "failing": "fail", "filing": "file", "happy": "happi", "sky": "sky",
    "relational": "relat", "conditional": "condit", "rational": "ration", "digitizer": "digit",
    "vietnamization": "vietnam", "predication": "predic", "operator": "oper", "feudalism": "feudal",
    "decisiveness": "decis", "hopefulness": "hope", "callousness": "callous", "formaliti": "formal",
    "sensitiviti": "sensit", "sensibiliti": "sensibl", "triplicate": "triplic", "formative": "form",
    "formalize": "formal", "electriciti": "electr", "electrical": "electr", "hopeful": "hope",
    "goodness": "good", "revival": "reviv", "allowance": "allow", "inference": "infer",
    "airliner": "airlin", "adjustable": "adjust", "defensible": "defens", "irritant": "irrit",
    "replacement": "replac", "adjustment": "adjust", "dependent": "depend", "adoption": "adopt",
    "communism": "commun", "activate": "activ", "angulariti": "angular", "homologous": "homolog",
    "effective": "effect", "probate": "probat", "rate": "rate", "cease": "ceas",
    "controll": "control", "roll": "roll",
}


def test_porter_canonical_pairs() -> None:
    for word, expected in PORTER_PAIRS.items():
        assert stem(word) == expected, f"{word} -> {stem(word)} (expected {expected})"


def test_morphological_variants_unify() -> None:
    # the whole point for retrieval: a query variant and a document variant
    # must collapse to the same stem (these were 0-hit misses on the demo).
    for a, b in [("factions", "faction"), ("conform", "conformity"),
                 ("decisions", "decision"), ("running", "run"), ("beliefs", "belief")]:
        assert stem(a) == stem(b), f"{a} ({stem(a)}) != {b} ({stem(b)})"


def test_short_words_unchanged() -> None:
    for word in ("be", "to", "is", "ax", "ok"):
        assert stem(word) == word


def test_stopwords_are_lowercase_and_present() -> None:
    assert "the" in STOPWORDS and "and" in STOPWORDS
    assert all(w == w.lower() for w in STOPWORDS)


def test_matches_nltk_reference_when_available() -> None:
    porter = pytest.importorskip("nltk.stem.porter")
    ref = porter.PorterStemmer(mode=porter.PorterStemmer.ORIGINAL_ALGORITHM)
    vocab = list(PORTER_PAIRS) + ["factions", "conformity", "decisions", "markets", "judgments"]
    mismatches = [(w, stem(w), ref.stem(w)) for w in vocab if stem(w) != ref.stem(w)]
    assert not mismatches, f"diverges from NLTK Porter: {mismatches}"
