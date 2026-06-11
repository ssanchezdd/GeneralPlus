from __future__ import annotations

import os
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1_536,
        batch_size: int = 64,
    ) -> None:
        if dimensions != 1_536:
            raise ValueError(
                "The current database schema requires 1536-dimensional embeddings"
            )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for production embeddings")
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "The openai package is required. Install backend/requirements.txt."
            ) from error

        client = OpenAI(api_key=self.api_key)
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            batch_vectors = [list(item.embedding) for item in ordered]
            if len(batch_vectors) != len(batch):
                raise RuntimeError("Embedding API returned an invalid vector count")
            if any(len(vector) != self.dimensions for vector in batch_vectors):
                raise RuntimeError("Embedding API returned an invalid vector dimension")
            vectors.extend(batch_vectors)
        return vectors
