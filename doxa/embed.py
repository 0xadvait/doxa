"""Embedding helpers for optional semantic retrieval."""

from __future__ import annotations

from typing import Any

from .schema import DoxaError


def embed_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """Embed text with fastembed. Requires the embeddings extra."""

    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise DoxaError("Semantic search requires embeddings: install doxa[embeddings].") from exc

    model_name = str(config.get("embeddings", {}).get("model", "BAAI/bge-small-en-v1.5"))
    model = TextEmbedding(model_name=model_name)
    return [vector.tolist() for vector in model.embed(texts)]


def embed_query(query: str, config: dict[str, Any]) -> list[float]:
    """Embed a search query for asymmetric retrieval.

    Documents are indexed with ``embed_texts`` (passage embeddings); queries
    should carry the model's query instruction (e.g. bge's "Represent this
    sentence for searching relevant passages:"). fastembed's ``query_embed``
    applies the right instruction per model, which measurably improves retrieval
    quality over embedding the query as a plain passage. Falls back gracefully.
    """
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise DoxaError("Semantic search requires embeddings: install doxa[embeddings].") from exc

    model_name = str(config.get("embeddings", {}).get("model", "BAAI/bge-small-en-v1.5"))
    model = TextEmbedding(model_name=model_name)
    name = model_name.lower()
    # bge-*-en-v1.5 use an explicit query instruction for short-query -> passage
    # retrieval; passages are embedded plain (in index_postgres), so prepending it
    # to the query gives the documented asymmetric setup. No re-index needed.
    if "bge" in name and "-en" in name and "v1.5" in name:
        text = "Represent this sentence for searching relevant passages: " + query
        return [vector.tolist() for vector in model.embed([text])][0]
    query_embed = getattr(model, "query_embed", None)
    if callable(query_embed):
        try:
            return [vector.tolist() for vector in query_embed([query])][0]
        except Exception:  # noqa: BLE001 - fall back to symmetric embedding
            return [vector.tolist() for vector in model.embed([query])][0]
    return [vector.tolist() for vector in model.embed([query])][0]

