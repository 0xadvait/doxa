# Retrieval

Keyword retrieval is pure Python BM25:

```bash
doxa query "self-reliance" --search keyword
```

Semantic retrieval needs embeddings and Postgres/pgvector:

```bash
python -m pip install -e ".[embeddings,postgres]"
export DOXA_POSTGRES_DSN=postgresql://...
doxa index
doxa query "political conflict" --search semantic
```

Hybrid retrieval uses reciprocal rank fusion with `k=60` by default. It combines
keyword and semantic rankings when both are available. If semantic search is not
configured, `doxa query --search hybrid` falls back to keyword and prints a
warning.

