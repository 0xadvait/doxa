"""Porter (1980) stemmer + English stopwords, stdlib-only.

Used to normalize tokens for keyword (BM25) retrieval so morphological variants
match: ``factions`` -> ``faction``, ``conform``/``conformity`` -> ``conform``.

Stemming and stopword removal affect ONLY the in-memory search index and the
query -- stored beliefs and quotes are never modified, so the verbatim guarantee
is untouched. Keeping this dependency-free preserves doxa's zero-setup keyword
search (no NLTK, no model download).
"""

from __future__ import annotations

_VOWELS = frozenset("aeiou")

# Conservative English stopword list. Small on purpose: BM25's IDF already
# down-weights ubiquitous terms, so this only trims obvious noise words.
STOPWORDS = frozenset(
    """
    a an and are as at be been being but by can could did do does for from had
    has have how i if in into is it its of on or our that the their them then
    there these they this those to was were what when where which who will with
    would you your
    """.split()
)


def _is_consonant(word: str, i: int) -> bool:
    ch = word[i]
    if ch in _VOWELS:
        return False
    if ch == "y":
        return i == 0 or not _is_consonant(word, i - 1)
    return True


def _measure(word: str) -> int:
    """Porter's m: the number of vowel-consonant sequences in the word."""
    n = 0
    i = 0
    length = len(word)
    while i < length and _is_consonant(word, i):
        i += 1
    while i < length:
        while i < length and not _is_consonant(word, i):
            i += 1
        if i >= length:
            break
        n += 1
        while i < length and _is_consonant(word, i):
            i += 1
    return n


def _has_vowel(word: str) -> bool:
    return any(not _is_consonant(word, i) for i in range(len(word)))


def _ends_double_consonant(word: str) -> bool:
    return len(word) >= 2 and word[-1] == word[-2] and _is_consonant(word, len(word) - 1)


def _cvc(word: str) -> bool:
    """True if word ends consonant-vowel-consonant and the last is not w/x/y."""
    if len(word) < 3:
        return False
    i = len(word) - 1
    if not (_is_consonant(word, i - 2) and not _is_consonant(word, i - 1) and _is_consonant(word, i)):
        return False
    return word[i] not in "wxy"


def _step1a(w: str) -> str:
    if w.endswith("sses"):
        return w[:-2]
    if w.endswith("ies"):
        return w[:-2]
    if w.endswith("ss"):
        return w
    if w.endswith("s"):
        return w[:-1]
    return w


def _step1b(w: str) -> str:
    if w.endswith("eed"):
        return w[:-1] if _measure(w[:-3]) > 0 else w
    changed = False
    if w.endswith("ed") and _has_vowel(w[:-2]):
        w = w[:-2]
        changed = True
    elif w.endswith("ing") and _has_vowel(w[:-3]):
        w = w[:-3]
        changed = True
    if changed:
        if w.endswith(("at", "bl", "iz")):
            return w + "e"
        if _ends_double_consonant(w) and not w.endswith(("l", "s", "z")):
            return w[:-1]
        if _measure(w) == 1 and _cvc(w):
            return w + "e"
    return w


def _step1c(w: str) -> str:
    if w.endswith("y") and _has_vowel(w[:-1]):
        return w[:-1] + "i"
    return w


_STEP2 = [
    ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
    ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"),
    ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
    ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
    ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"),
]
_STEP3 = [
    ("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"),
    ("ical", "ic"), ("ful", ""), ("ness", ""),
]
_STEP4 = [
    "al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment",
    "ent", "ou", "ism", "ate", "iti", "ous", "ive", "ize",
]


def _apply_table(w: str, table: list[tuple[str, str]]) -> str:
    for suffix, repl in table:
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            return stem + repl if _measure(stem) > 0 else w
    return w


def _step4(w: str) -> str:
    for suffix in _STEP4:
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            return stem if _measure(stem) > 1 else w
    if w.endswith("ion"):
        stem = w[:-3]
        if _measure(stem) > 1 and stem and stem[-1] in ("s", "t"):
            return stem
    return w


def _step5(w: str) -> str:
    if w.endswith("e"):
        stem = w[:-1]
        if _measure(stem) > 1 or (_measure(stem) == 1 and not _cvc(stem)):
            w = stem
    if _measure(w) > 1 and _ends_double_consonant(w) and w.endswith("l"):
        w = w[:-1]
    return w


def stem(word: str) -> str:
    """Return the Porter stem of a single lowercase word."""
    if len(word) <= 2:
        return word
    word = _step1a(word)
    word = _step1b(word)
    word = _step1c(word)
    word = _apply_table(word, _STEP2)
    word = _apply_table(word, _STEP3)
    word = _step4(word)
    word = _step5(word)
    return word
