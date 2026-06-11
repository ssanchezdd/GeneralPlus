# Pipeline RAG

## Flujo implementado

`ingest_guidelines.py` coordina descarga, validación, extracción, limpieza,
chunking, embeddings e indexación. La configuración documental vive en el
manifiesto y la evidencia descargada queda fijada por SHA-256 en el lock.

```text
PDF oficial
  -> validación de origen y seguridad
  -> texto por página
  -> limpieza conservadora
  -> chunks clínicos con metadatos
  -> revisión técnica y clínica
  -> text-embedding-3-small, 1536 dimensiones
  -> PostgreSQL + pgvector
  -> filtro de metadatos + distancia coseno
  -> respuesta con fuentes o abstención
```

La especificación operativa y los comandos están en
[`guideline_ingestion.md`](guideline_ingestion.md).

## Recuperación

`backend/rag/pgvector.py` aplica:

1. embedding de la consulta con el mismo modelo del corpus;
2. filtros de condición, tipo de fuente y elegibilidad;
3. distancia coseno mediante el operador `<=>`;
4. límite `top_k`;
5. conversión a fuentes con páginas, editorial, año y URL.

`backend/rag/local_index.py` ofrece una prueba léxica reproducible sobre los
JSONL preparados. No se usa como sustituto silencioso del índice vectorial de
producción.

## Respuesta segura

Toda respuesta sustentada incluye `Basado en:` y una lista de fuentes. Cuando
no hay evidencia suficiente se devuelve exactamente:

> No encontré una fuente suficiente en las guías cargadas. No puedo responder
> con seguridad.

Las consultas tiempo-dependientes conservan flags de seguridad independientes
del score de recuperación. El generador no debe convertir una coincidencia
semántica en una recomendación clínica si el fragmento no respalda la
afirmación.

## Persistencia

`backend/schema.sql` crea:

- `guideline_documents`, con estado, hash, revisión y modelo de embedding;
- `guideline_chunks`, con contenido, metadatos y `vector(1536)`;
- índices B-tree para filtros;
- índice HNSW con `vector_cosine_ops`.

La versión documental se reemplaza en una transacción solo con `--force`.
