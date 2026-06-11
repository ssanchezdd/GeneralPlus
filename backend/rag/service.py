from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from backend.evaluators.safety import evaluate_query_safety


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    disease_id: str
    source_type: str
    title: str
    text: str
    source_url: str
    page: int | None
    scope: str


@dataclass(frozen=True)
class RetrievalFilters:
    disease_ids: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoredSource:
    id: str
    title: str
    source_url: str
    page: int | None
    score: float
    scope: str


@dataclass(frozen=True)
class RagResult:
    summary: str
    sources: list[ScoredSource]
    confidence: str
    abstained: bool
    safety_flags: list[str]


class Retriever(Protocol):
    def search(
        self, query: str, filters: RetrievalFilters, top_k: int
    ) -> list[tuple[EvidenceRecord, float]]: ...


def _normalize(text: str) -> set[str]:
    value = "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )
    return {
        token
        for token in re.findall(r"[a-z0-9/]+", value)
        if len(token) > 2
    }


class InMemoryRetriever:
    """Deterministic development adapter; production uses pgvector."""

    def __init__(self, records: list[EvidenceRecord]) -> None:
        self.records = records

    def search(
        self, query: str, filters: RetrievalFilters, top_k: int
    ) -> list[tuple[EvidenceRecord, float]]:
        query_tokens = _normalize(query)
        scored: list[tuple[EvidenceRecord, float]] = []
        for record in self.records:
            if filters.disease_ids and record.disease_id not in filters.disease_ids:
                continue
            if filters.source_types and record.source_type not in filters.source_types:
                continue
            corpus = _normalize(f"{record.title} {record.text} {record.scope}")
            score = len(query_tokens & corpus) / max(1, len(query_tokens))
            if score > 0:
                scored.append((record, score))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


class RagService:
    def __init__(self, retriever: Retriever, minimum_score: float = 0.08) -> None:
        self.retriever = retriever
        self.minimum_score = minimum_score

    def query(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        top_k: int = 5,
    ) -> RagResult:
        safety_flags = evaluate_query_safety(query)
        records = self.retriever.search(
            query, filters or RetrievalFilters(), top_k=top_k
        )
        relevant = [item for item in records if item[1] >= self.minimum_score]
        if not relevant:
            return RagResult(
                summary=(
                    "No hay evidencia recuperada suficiente para responder. "
                    "Consulte la fuente oficial o el protocolo institucional."
                ),
                sources=[],
                confidence="baja",
                abstained=True,
                safety_flags=safety_flags,
            )

        sources = [
            ScoredSource(
                id=record.id,
                title=record.title,
                source_url=record.source_url,
                page=record.page,
                score=round(score, 4),
                scope=record.scope,
            )
            for record, score in relevant
        ]
        primary = relevant[0][0]
        return RagResult(
            summary=primary.text,
            sources=sources,
            confidence="moderada" if relevant[0][1] < 0.5 else "alta",
            abstained=False,
            safety_flags=safety_flags,
        )

