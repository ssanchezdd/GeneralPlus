from __future__ import annotations

from backend.ingest.embeddings import EmbeddingProvider
from backend.rag.service import EvidenceRecord, RetrievalFilters


class PgVectorRetriever:
    def __init__(
        self,
        database_url: str,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.database_url = database_url
        self.embedding_provider = embedding_provider

    def search(
        self,
        query: str,
        filters: RetrievalFilters,
        top_k: int,
    ) -> list[tuple[EvidenceRecord, float]]:
        try:
            import psycopg
            from pgvector.psycopg import register_vector
        except ImportError as error:
            raise RuntimeError(
                "psycopg and pgvector are required for vector retrieval"
            ) from error

        query_vector = self.embedding_provider.embed([query])[0]
        clauses = ["d.status = 'ready'", "c.retrieval_eligible = true"]
        parameters: list[object] = [query_vector]
        if filters.disease_ids:
            clauses.append("c.condition = ANY(%s)")
            parameters.append(filters.disease_ids)
        if filters.source_types:
            clauses.append("c.source_type = ANY(%s)")
            parameters.append(filters.source_types)
        parameters.append(top_k)
        sql = f"""
            SELECT
              c.id::text,
              c.condition,
              c.source_type,
              c.title,
              c.content,
              c.url,
              c.page_start,
              c.page_end,
              COALESCE(d.metadata->>'scope_note', ''),
              c.publisher,
              c.year,
              c.guideline_id,
              1 - (c.embedding <=> %s) AS score
            FROM guideline_chunks c
            JOIN guideline_documents d ON d.id = c.document_id
            WHERE {' AND '.join(clauses)}
            ORDER BY c.embedding <=> %s
            LIMIT %s
        """
        # The vector is used once for the score and once for ordering.
        parameters.insert(-1, query_vector)

        with psycopg.connect(self.database_url) as connection:
            register_vector(connection)
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                rows = cursor.fetchall()

        return [
            (
                EvidenceRecord(
                    id=row[0],
                    disease_id=row[1],
                    source_type=row[2],
                    title=row[3],
                    text=row[4],
                    source_url=row[5],
                    page=row[6],
                    page_end=row[7],
                    scope=row[8],
                    publisher=row[9],
                    year=row[10],
                    guideline_id=row[11],
                ),
                float(row[12]),
            )
            for row in rows
        ]
