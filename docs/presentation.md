# Presentation modes

doxa retrieves evidence; the agent reading the output composes the prose answer.
A **presentation mode** is an optional voice for that final step. It changes the
voice and shape of the answer, never the grounding.

The default is `plain`: no directive, output unchanged. The flagship optional
mode is `hawking`.

## Use it

```bash
doxa present --list                 # list modes with one-line summaries
doxa present hawking                # print the composition directive
doxa present hawking --json         # machine-readable profile

doxa query "did time have a beginning?" --present hawking
doxa query "did time have a beginning?" --answer --present hawking   # pairs with the evidence brief
```

With a non-plain mode, `doxa query` prints a directive block before the
evidence:

```text
=== doxa presentation directive: hawking ===
...
=== end presentation directive ===

1. <belief> ...
```

An agent reads the directive, then writes the answer in that voice using only
the retrieved beliefs and quotes.

### Output shapes

- Text: the directive is prepended, then the usual numbered results.
- `--json` with `plain`: a bare list of results (unchanged, backward compatible).
- `--json` with a non-plain mode: `{"presentation": {...}, "results": [...]}`.

### Make it the default

```yaml
# doxa.yaml
presentation:
  default: hawking
```

A `--present` flag on `doxa query` overrides the configured default.

## The hawking mode

It is distilled from how Stephen Hawking presented evidence in the first two
chapters of *A Brief History of Time*. The directive carries an arc, a set of
moves (each with a short verbatim exemplar), and hard constraints:

- Open on the old question -- wonder, not the apparatus.
- Stage a procession of minds: the retrieved beliefs are the cast, and the
  reader watches the picture change.
- Say the largest thing in the plainest sentence.
- Keep the strangeness intact; never simplify into a comfortable falsehood.
- Make the answer epistemology: name what kind of claim this is and how far it
  can be trusted.
- Hold humility and audacity together.
- Close on the human stakes of the question.

**It is voice, not license.** The directive restates the inviolable rule: every
belief and quote must still come from doxa's retrieved records, conviction is
still reported honestly, and nothing is invented. Rigor under the lyricism is
itself the Hawking move.

## Add a mode

Modes are data. Register a `PresentationProfile` in `doxa/present.py`:

```python
MY_PROFILE = PresentationProfile(
    name="my-voice",
    title="...",
    summary="...",
    arc=("...",),
    moves=(Move(name="...", directive="...", exemplar="..."),),
    constraints=("...",),
)
```

Add it to the `_PROFILES` registry and it becomes available to `doxa present`,
`doxa query --present`, and the `presentation.default` config key. A profile with
no `arc`/`moves`/`constraints` is treated as plain (no directive).
