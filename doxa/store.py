"""JSONL storage and optional Postgres indexing."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

from .config import data_file
from .schema import Belief, DoxaError, Quote, RetrievalResult, SourceRecord


_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def postgres_table_prefix(config: dict[str, Any]) -> str:
    """Return a safe Postgres table prefix for dynamic identifiers."""

    prefix = str(config.get("postgres", {}).get("table_prefix", "doxa"))
    if not _SQL_IDENTIFIER_RE.fullmatch(prefix):
        raise DoxaError(
            "postgres.table_prefix must be a SQL identifier: start with a letter/underscore "
            "and contain only letters, numbers, and underscores."
        )
    return prefix


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

    def has_source(self, source_id: str) -> bool:
        return any(source.id == source_id for source in self.sources())

    def remove_source(self, source_id: str) -> dict[str, int]:
        """Delete a source and every belief/quote derived from it; return removed counts."""
        sources = self.sources()
        target = next((source for source in sources if source.id == source_id), None)
        if target is None:
            raise DoxaError(f"No ingested source with id '{source_id}'. Run `doxa sources list`.")
        legacy_key = (target.title, target.url)

        def matches_target(ref) -> bool:
            ref_id = getattr(ref, "id", "")
            if ref_id:
                return ref_id == source_id
            return (ref.title, ref.url) == legacy_key

        beliefs = self.beliefs()
        quotes = self.quotes()
        kept_beliefs = [belief for belief in beliefs if not matches_target(belief.source)]
        kept_quotes = [quote for quote in quotes if not matches_target(quote.source)]
        kept_sources = [source for source in sources if source.id != source_id]
        self.write_all(kept_beliefs, kept_quotes, kept_sources)
        return {
            "beliefs": len(beliefs) - len(kept_beliefs),
            "quotes": len(quotes) - len(kept_quotes),
            "sources": 1,
        }

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

    from psycopg2 import sql

    from .embed import embed_texts

    store = JsonlStore(config)
    beliefs = store.beliefs()
    quotes = store.quotes()
    if not beliefs:
        raise DoxaError(f"No beliefs found at {store.beliefs_path}")
    prefix = postgres_table_prefix(config)
    beliefs_table = f"{prefix}_beliefs"
    quotes_table = f"{prefix}_quotes"
    links_table = f"{prefix}_belief_quotes"
    index_name = f"{prefix}_beliefs_embedding_hnsw"
    dimension = int(config.get("embeddings", {}).get("dimension", 384))
    if dimension <= 0 or dimension > 8192:
        raise DoxaError("embeddings.dimension must be between 1 and 8192.")
    # Open the DB connection before embedding so DSN/connectivity errors fail fast,
    # rather than after a slow embed (which can download a model on first run).
    conn = postgres_connect(config)
    texts = [belief.belief + "\n" + belief.reasoning for belief in beliefs]
    vectors = embed_texts(texts, config)
    belief_ids = [belief.id for belief in beliefs]
    quote_ids = [quote.id for quote in quotes]
    try:
        with conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                  id text PRIMARY KEY,
                  payload jsonb NOT NULL,
                  embedding vector({})
                )
                """
                ).format(sql.Identifier(beliefs_table), sql.SQL(str(dimension)))
            )
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                  id text PRIMARY KEY,
                  payload jsonb NOT NULL
                )
                """
                ).format(sql.Identifier(quotes_table))
            )
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {} (
                  belief_id text NOT NULL,
                  quote_id text NOT NULL,
                  PRIMARY KEY (belief_id, quote_id)
                )
                """
                ).format(sql.Identifier(links_table))
            )
            for belief, vector in zip(beliefs, vectors):
                cur.execute(
                    sql.SQL(
                        "INSERT INTO {} (id, payload, embedding) VALUES (%s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, embedding = EXCLUDED.embedding"
                    ).format(sql.Identifier(beliefs_table)),
                    (belief.id, json.dumps(belief.to_dict()), vector),
                )
            for quote in quotes:
                cur.execute(
                    sql.SQL(
                        "INSERT INTO {} (id, payload) VALUES (%s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload"
                    ).format(sql.Identifier(quotes_table)),
                    (quote.id, json.dumps(quote.to_dict())),
                )
            cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(links_table)))
            for quote in quotes:
                for belief_id in quote.belief_ids:
                    cur.execute(
                        sql.SQL("INSERT INTO {} (belief_id, quote_id) VALUES (%s, %s) ON CONFLICT DO NOTHING").format(
                            sql.Identifier(links_table)
                        ),
                        (belief_id, quote.id),
                    )
            cur.execute(
                sql.SQL("DELETE FROM {} WHERE NOT (id = ANY(%s))").format(sql.Identifier(beliefs_table)),
                (belief_ids,),
            )
            if quote_ids:
                cur.execute(
                    sql.SQL("DELETE FROM {} WHERE NOT (id = ANY(%s))").format(sql.Identifier(quotes_table)),
                    (quote_ids,),
                )
            else:
                cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(quotes_table)))
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} USING hnsw (embedding vector_cosine_ops)").format(
                    sql.Identifier(index_name), sql.Identifier(beliefs_table)
                )
            )
    finally:
        conn.close()
    return {"beliefs": len(beliefs), "quotes": len(quotes)}
