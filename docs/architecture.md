# Architecture

doxa is deliberately small in the core path:

1. Load trusted source text.
2. Split it into chunks.
3. Build an extraction prompt from a user-defined lens.
4. Ask a pluggable provider for strict JSON.
5. Verify each quote is a real substring of the source after whitespace normalization.
6. Store beliefs, quotes, and source text as JSONL.
7. Retrieve with keyword BM25, optional pgvector semantic search, or hybrid RRF.
8. Optionally emit a presentation directive so the consuming agent composes the answer in a chosen voice.

JSONL is the source of truth. Postgres/pgvector is an optional index, not the
canonical store.

## Where answers are composed

doxa retrieves evidence; the agent reading the output composes the prose answer
(`doxa query --answer` is the built-in deterministic renderer). That split is
where presentation modes live. A `PresentationProfile` (`doxa/present.py`) is an
optional composition directive the CLI prints alongside the evidence at query
time. It shapes voice and structure only -- the retrieved beliefs and verbatim
quotes remain the sole evidence, so a mode can never become a license to
embellish. The default is `plain` (no directive). See [presentation.md](presentation.md).

