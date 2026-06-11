from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.ingest.repository import PgVectorGuidelineRepository


def main() -> None:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://criterio:criterio-local-only@127.0.0.1:5432/criterio",
    )
    repository = PgVectorGuidelineRepository(database_url)
    repository.initialize_schema(REPOSITORY_ROOT / "backend/schema.sql")

    with psycopg.connect(database_url) as connection:
        register_vector(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            version = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT
                  to_regclass('public.guideline_documents'),
                  to_regclass('public.guideline_chunks')
                """
            )
            tables = cursor.fetchone()
            cursor.execute(
                "CREATE TEMP TABLE vector_smoke (id int, embedding vector(3))"
            )
            cursor.execute(
                """
                INSERT INTO vector_smoke VALUES
                  (1, '[1,0,0]'),
                  (2, '[0,1,0]')
                """
            )
            cursor.execute(
                """
                SELECT id
                FROM vector_smoke
                ORDER BY embedding <=> '[0.9,0.1,0]'
                LIMIT 1
                """
            )
            nearest = cursor.fetchone()[0]

    if nearest != 1:
        raise RuntimeError(f"Unexpected nearest neighbor: {nearest}")
    print(
        {
            "pgvector_version": version,
            "tables": tables,
            "nearest_neighbor": nearest,
        }
    )


if __name__ == "__main__":
    main()
