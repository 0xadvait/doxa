# Architecture

doxa is deliberately small in the core path:

1. Load trusted source text.
2. Split it into chunks.
3. Build an extraction prompt from a user-defined lens.
4. Ask a pluggable provider for strict JSON.
5. Verify each quote is a real substring of the source after whitespace normalization.
6. Store beliefs, quotes, and source text as JSONL.
7. Retrieve with keyword BM25, optional pgvector semantic search, or hybrid RRF.

JSONL is the source of truth. Postgres/pgvector is an optional index, not the
canonical store.

