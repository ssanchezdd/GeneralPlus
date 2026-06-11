from __future__ import annotations

import os

from backend.ingest.embeddings import OpenAIEmbeddingProvider
from backend.rag.pgvector import PgVectorRetriever
from backend.rag.service import EvidenceRecord, InMemoryRetriever, RagService


def build_rag_service() -> tuple[RagService, str]:
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    if database_url and api_key:
        embeddings = OpenAIEmbeddingProvider(api_key=api_key)
        return (
            RagService(PgVectorRetriever(database_url, embeddings)),
            "pgvector",
        )

    # Development fallback only. It is never presented as a production index.
    retriever = InMemoryRetriever(
        records=[
            EvidenceRecord(
                id="hta-scope",
                disease_id="hypertension",
                source_type="GPC",
                title="Alcance GPC hipertensión arterial primaria",
                text=(
                    "La guía cubre prevención, diagnóstico, tratamiento y "
                    "seguimiento de HTA primaria y excluye urgencia "
                    "hipertensiva y embarazo."
                ),
                source_url=(
                    "https://www.minsalud.gov.co/sites/rid/Lists/"
                    "BibliotecaDigital/RIDE/DE/CA/"
                    "gpc-profesionales-hipertension-arterial-primaria.pdf"
                ),
                page=11,
                page_end=12,
                scope=(
                    "HTA primaria en adultos; no cubre urgencias ni embarazo."
                ),
                publisher="Ministerio de Salud y Protección Social / IETS",
                year=2017,
                guideline_id="col-gpc-hta-2017-profesionales",
            )
        ]
    )
    return RagService(retriever=retriever), "demonstration"
