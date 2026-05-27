"""JSONL storage and optional Postgres indexing."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .config import data_file
from .schema import Belief, DoxaError, Quote, RetrievalResult, SourceRecord


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DoxaError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


class JsonlStore:
    """Source-of-truth store for beliefs, quotes, and source text."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.beliefs_path = data_file(config, "beliefs")
        self.quotes_path = data_file(config, "quotes")
        self.sources_path = data_file(config, "sources")

    def beliefs(self) -> list[Belief]:
        return [Belief.from_dict(row) for row in read_jsonl(self.beliefs_path)]

    def quotes(self) -> list[Quote]:
        return [Quote.from_dict(row) for row in read_jsonl(self.quotes_path)]

    def sources(self) -> list[SourceRecord]:
        return [SourceRecord.from_dict(row) for row in read_jsonl(self.sources_path)]

    def write_all(self, beliefs: list[Belief], quotes: list[Quote], sources: list[SourceRecord] | None = None) -> None:
        write_jsonl(self.beliefs_path, [belief.to_dict() for belief in beliefs])
        write_jsonl(self.quotes_path, [quote.to_dict() for quote in quotes])
        if sources is not None:
            write_jsonl(self.sources_path, [source.to_dict() for source in sources])

    def append(self, beliefs: list[Belief], quotes: list[Quote], sources: list[SourceRecord] | None = None) -> None:
        append_jsonl(self.beliefs_path, [belief.to_dict() for belief in beliefs])
        append_jsonl(self.quotes_path, [quote.to_dict() for quote in quotes])
        if sources:
            append_jsonl(self.sources_path, [source.to_dict() for source in sources])

    def linked_results(self, scored_beliefs: list[tuple[Belief, float]]) -> list[RetrievalResult]:
        quotes = self.quotes()
        by_belief: dict[str, list[Quote]] = {}
        for quote in quotes:
            for belief_id in quote.belief_ids:
                by_belief.setdefault(belief_id, []).append(quote)
        return [
            RetrievalResult(belief=belief, quotes=by_belief.get(belief.id, []), score=score)
            for belief, score in scored_beliefs
        ]


def postgres_connect(config: dict[str, Any]):
    try:
        import psycopg2
        from pgvector.psycopg2 import register_vector
    except ImportError as exc:
        raise DoxaError(
            "Postgres search requires extras: install doxa[postgres] (and doxa[embeddings] for semantic indexing)."
        ) from exc
    dsn_env = str(config.get("postgres", {}).get("dsn_env", "DOXA_POSTGRES_DSN"))
    dsn = os.environ.get(dsn_env)
    if not dsn:
        raise DoxaError(f"Set {dsn_env} to a PostgreSQL DSN before using semantic search or indexing.")
    conn = psycopg2.connect(dsn)
    register_vector(conn)
    return conn


def index_postgres(config: dict[str, Any]) -> dict[str, int]:
    """Create/update a pgvector index from JSONL data."""

    from .embed import embed_texts

    store = JsonlStore(config)
    beliefs = store.beliefs()
    quotes = store.quotes()
    if not beliefs:
        raise DoxaError(f"No beliefs found at {store.beliefs_path}")
    prefix = str(config.get("postgres", {}).get("table_prefix", "doxa"))
    dimension = int(config.get("embeddings", {}).get("dimension", 384))
    texts = [belief.belief + "\n" + belief.reasoning for belief in beliefs]
    vectors = embed_texts(texts, config)

    conn = postgres_connect(config)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {prefix}_beliefs (
                  id text PRIMARY KEY,
                  payload jsonb NOT NULL,
                  embedding vector({dimension})
                )
                """
            )
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {prefix}_quotes (
                  id text PRIMARY KEY,
                  payload jsonb NOT NULL
                )
                """
            )
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {prefix}_belief_quotes (
                  belief_id text NOT NULL,
                  quote_id text NOT NULL,
                  PRIMARY KEY (belief_id, quote_id)
                )
                """
            )
            for belief, vector in zip(beliefs, vectors):
                cur.execute(
                    f"INSERT INTO {prefix}_beliefs (id, payload, embedding) VALUES (%s, %s, %s) "
                    f"ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, embedding = EXCLUDED.embedding",
                    (belief.id, json.dumps(belief.to_dict()), vector),
                )
            for quote in quotes:
                cur.execute(
                    f"INSERT INTO {prefix}_quotes (id, payload) VALUES (%s, %s) "
                    f"ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload",
                    (quote.id, json.dumps(quote.to_dict())),
                )
                for belief_id in quote.belief_ids:
                    cur.execute(
                        f"INSERT INTO {prefix}_belief_quotes (belief_id, quote_id) VALUES (%s, %s) "
                        f"ON CONFLICT DO NOTHING",
                        (belief_id, quote.id),
                    )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {prefix}_beliefs_embedding_hnsw "
                f"ON {prefix}_beliefs USING hnsw (embedding vector_cosine_ops)"
            )
    finally:
        conn.close()
    return {"beliefs": len(beliefs), "quotes": len(quotes)}

