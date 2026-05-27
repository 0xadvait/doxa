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

