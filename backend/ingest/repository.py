from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from backend.ingest.chunker import Chunk, is_retrieval_eligible
from backend.ingest.extractor import PDFExtractionReport
from backend.ingest.models import DownloadRecord, GuidelineManifestEntry


class ExistingGuidelineError(RuntimeError):
    pass


class PgVectorGuidelineRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("A PostgreSQL database URL is required")
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
            from pgvector.psycopg import register_vector
        except ImportError as error:
            raise RuntimeError(
                "psycopg and pgvector are required. "
                "Install backend/requirements.txt."
            ) from error
        connection = psycopg.connect(self.database_url)
        register_vector(connection)
        return connection

    def initialize_schema(self, schema_path: str | Path) -> None:
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError(
                "psycopg is required. Install backend/requirements.txt."
            ) from error
        sql = Path(schema_path).read_text(encoding="utf-8")
        # The vector adapter cannot be registered until CREATE EXTENSION runs.
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)

    def is_ingested(self, guideline_id: str) -> tuple[bool, str | None]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status, sha256
                    FROM guideline_documents
                    WHERE guideline_id = %s
                    """,
                    (guideline_id,),
                )
                row = cursor.fetchone()
        return (bool(row and row[0] == "ready"), row[1] if row else None)

    def upsert(
        self,
        entry: GuidelineManifestEntry,
        download: DownloadRecord,
        extraction: PDFExtractionReport,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        *,
        embedding_model: str,
        force: bool,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts do not match")

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, sha256, status
                    FROM guideline_documents
                    WHERE guideline_id = %s
                    FOR UPDATE
                    """,
                    (entry.id,),
                )
                existing = cursor.fetchone()
                if existing and not force:
                    raise ExistingGuidelineError(
                        f"{entry.id} is already present with SHA-256 "
                        f"{existing[1]}; pass --force to replace it"
                    )

                cursor.execute(
                    """
                    INSERT INTO guideline_documents (
                      guideline_id, title, institution, source_type, source_url,
                      publication_year, version, sha256, file_bytes, page_count,
                      status, metadata, updated_at
                    )
                    VALUES (
                      %(guideline_id)s, %(title)s, %(publisher)s, %(source_type)s,
                      %(url)s, %(year)s, %(version)s, %(sha256)s, %(file_bytes)s,
                      %(page_count)s, 'processing', %(metadata)s::jsonb, now()
                    )
                    ON CONFLICT (guideline_id) DO UPDATE SET
                      title = EXCLUDED.title,
                      institution = EXCLUDED.institution,
                      source_type = EXCLUDED.source_type,
                      source_url = EXCLUDED.source_url,
                      publication_year = EXCLUDED.publication_year,
                      version = EXCLUDED.version,
                      sha256 = EXCLUDED.sha256,
                      file_bytes = EXCLUDED.file_bytes,
                      page_count = EXCLUDED.page_count,
                      status = 'processing',
                      metadata = EXCLUDED.metadata,
                      updated_at = now()
                    RETURNING id
                    """,
                    {
                        "guideline_id": entry.id,
                        "title": entry.title,
                        "publisher": entry.publisher,
                        "source_type": entry.source_type,
                        "url": entry.url,
                        "year": entry.year,
                        "version": str(entry.year),
                        "sha256": download.sha256,
                        "file_bytes": download.bytes,
                        "page_count": extraction.pages_total,
                        "metadata": json.dumps(
                            entry.metadata(), ensure_ascii=False
                        ),
                    },
                )
                document_id = cursor.fetchone()[0]
                cursor.execute(
                    "DELETE FROM guideline_chunks WHERE document_id = %s",
                    (document_id,),
                )

                for ordinal, (chunk, embedding) in enumerate(
                    zip(chunks, embeddings, strict=True), start=1
                ):
                    cursor.execute(
                        """
                        INSERT INTO guideline_chunks (
                          document_id, ordinal, guideline_id, title, condition,
                          source_type, publisher, year, audience, priority,
                          country, clinical_area, section_guess,
                          recommendation_type_guess, population, care_level,
                          urgency, heading, page_start, page_end, url, content,
                          retrieval_eligible,
                          source_sha256, embedding_model, embedding, metadata
                        )
                        VALUES (
                          %(document_id)s, %(ordinal)s, %(guideline_id)s,
                          %(title)s, %(condition)s, %(source_type)s,
                          %(publisher)s, %(year)s, %(audience)s, %(priority)s,
                          %(country)s, %(clinical_area)s, %(section)s,
                          %(recommendation_type)s, %(population)s,
                          %(care_level)s, %(urgency)s, %(heading)s,
                          %(page_start)s, %(page_end)s, %(url)s, %(content)s,
                          %(retrieval_eligible)s,
                          %(source_sha256)s, %(embedding_model)s, %(embedding)s,
                          %(metadata)s::jsonb
                        )
                        """,
                        {
                            "document_id": document_id,
                            "ordinal": ordinal,
                            "guideline_id": entry.id,
                            "title": entry.title,
                            "condition": entry.condition,
                            "source_type": entry.source_type,
                            "publisher": entry.publisher,
                            "year": entry.year,
                            "audience": entry.audience,
                            "priority": entry.priority,
                            "country": entry.country,
                            "clinical_area": entry.clinical_area,
                            "section": chunk.section_guess,
                            "recommendation_type": (
                                chunk.recommendation_type_guess
                            ),
                            "population": (
                                chunk.population
                                if chunk.population != "no_especificada"
                                else (
                                    entry.population[0]
                                    if entry.population
                                    else chunk.population
                                )
                            ),
                            "care_level": (
                                chunk.care_level
                                if chunk.care_level != "no_especificado"
                                else (
                                    entry.care_level[0]
                                    if entry.care_level
                                    else chunk.care_level
                                )
                            ),
                            "urgency": chunk.urgency,
                            "heading": chunk.heading,
                            "page_start": chunk.page_start,
                            "page_end": chunk.page_end,
                            "url": entry.url,
                            "content": chunk.text,
                            "retrieval_eligible": is_retrieval_eligible(chunk),
                            "source_sha256": download.sha256,
                            "embedding_model": embedding_model,
                            "embedding": embedding,
                            "metadata": json.dumps(
                                {
                                    "token_estimate": chunk.token_estimate,
                                    "scope_note": entry.scope_note,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    )

                cursor.execute(
                    """
                    UPDATE guideline_documents
                    SET status = 'ready', updated_at = now()
                    WHERE id = %s
                    """,
                    (document_id,),
                )
        return len(chunks)
