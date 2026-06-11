from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.rag.service import (
    EvidenceRecord,
    InMemoryRetriever,
    RagService,
    RetrievalFilters,
)


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


class QueryResponse(BaseModel):
    summary: str
    sources: list[SourceResponse]
    confidence: str
    abstained: bool
    safety_flags: list[str]


app = FastAPI(
    title="Criterio RAG API",
    version="0.1.0",
    description="Production contract for the Colombian clinical-support RAG.",
)

# Development-only records prove the API contract. Production replaces this
# retriever with the pgvector adapter documented in docs/rag_pipeline.md.
retriever = InMemoryRetriever(
    records=[
        EvidenceRecord(
            id="hta-scope",
            disease_id="hypertension",
            source_type="GPC",
            title="Alcance GPC hipertensión arterial primaria",
            text=(
                "La guía cubre prevención, diagnóstico, tratamiento y seguimiento "
                "de HTA primaria y excluye urgencia hipertensiva y embarazo."
            ),
            source_url=(
                "https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/"
                "RIDE/DE/CA/gpc-profesionales-hipertension-arterial-primaria.pdf"
            ),
            page=11,
            scope="HTA primaria en adultos; no cubre urgencias ni embarazo.",
        )
    ]
)
service = RagService(retriever=retriever)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "criterio-rag-api"}


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

