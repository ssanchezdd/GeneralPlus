from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.ingest.chunker import Chunk, DocumentPage, chunk_pages


class DocumentExtractor(Protocol):
    def extract(self, location: str) -> list[DocumentPage]: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ChunkRepository(Protocol):
    def upsert(
        self,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        metadata: dict[str, str],
    ) -> int: ...


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    page_count: int
    chunk_count: int
    stored_count: int


class IngestionPipeline:
    def __init__(
        self,
        extractor: DocumentExtractor,
        embeddings: EmbeddingProvider,
        repository: ChunkRepository,
    ) -> None:
        self.extractor = extractor
        self.embeddings = embeddings
        self.repository = repository

    def ingest(
        self,
        document_id: str,
        location: str,
        metadata: dict[str, str],
    ) -> IngestionResult:
        pages = self.extractor.extract(location)
        chunks = chunk_pages(document_id, pages)
        vectors = self.embeddings.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding provider returned an invalid vector count")
        stored = self.repository.upsert(document_id, chunks, vectors, metadata)
        return IngestionResult(
            document_id=document_id,
            page_count=len(pages),
            chunk_count=len(chunks),
            stored_count=stored,
        )

