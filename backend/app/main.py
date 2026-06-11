from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.app.service_factory import build_rag_service
from backend.rag.citations import format_citation
from backend.rag.service import RetrievalFilters


class QueryRequest(BaseModel):
    query: str = Field(min_length=8, max_length=4_000)
    disease_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=12)


class SourceResponse(BaseModel):
    id: str
    title: str
    source_url: str
    page: int | None
    score: float
    scope: str
    page_end: int | None = None
    publisher: str | None = None
    year: int | None = None
    guideline_id: str | None = None


class QueryResponse(BaseModel):
    summary: str
    sources: list[SourceResponse]
    confidence: str
    abstained: bool
    safety_flags: list[str]
    based_on: list[str]


app = FastAPI(
    title="Criterio RAG API",
    version="0.1.0",
    description="Production contract for the Colombian clinical-support RAG.",
)

service, retrieval_mode = build_rag_service()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "criterio-rag-api",
        "retrieval_mode": retrieval_mode,
    }


@app.post("/v1/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = service.query(
        request.query,
        filters=RetrievalFilters(
            disease_ids=request.disease_ids,
            source_types=request.source_types,
        ),
        top_k=request.top_k,
    )
    return QueryResponse(
        summary=result.summary,
        sources=[SourceResponse(**asdict(source)) for source in result.sources],
        confidence=result.confidence,
        abstained=result.abstained,
        safety_flags=result.safety_flags,
        based_on=[format_citation(source) for source in result.sources],
    )


@app.post("/v1/documents", status_code=501)
def upload_document() -> None:
    raise HTTPException(
        status_code=501,
        detail=(
            "The upload contract is reserved. Connect the ingestion worker, "
            "object storage, antivirus scan, and pgvector adapter before enabling it."
        ),
    )
