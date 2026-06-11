# Pipeline RAG

## Arquitectura objetivo

```text
PDF/HTML oficial
  -> descarga controlada + hash + antivirus
  -> extracción con página y estructura
  -> revisión de encabezados y tablas
  -> chunks por sección clínica
  -> metadatos de población, enfermedad, ámbito y alcance
  -> embeddings
  -> PostgreSQL + pgvector
  -> recuperación híbrida + filtros
  -> reranking
  -> evaluación de seguridad
  -> respuesta estructurada con citas
  -> verificación afirmación-cita
  -> auditoría y feedback
```

## Chunking

`backend/ingest/chunker.py`:

- normaliza saltos de línea sin borrar páginas;
- identifica encabezados en mayúsculas;
- crea chunks con objetivo de 700 tokens;
- conserva 90 tokens de solapamiento;
- registra página inicial/final y encabezado.

Las tablas, algoritmos e imágenes requieren un extractor especializado y
revisión humana. No deben convertirse a texto plano sin comprobar su sentido.

## Metadatos

Campos mínimos:

- `disease_ids`
- `population_tags`: adulto, pediatría, gestante, puerperio
- `care_setting`: ambulatorio, urgencias, hospitalización
- `source_type`: GPC, RIAS, protocolo
- páginas y encabezado
- alcance y exclusiones
- fuerza y calidad de evidencia
- versión y hash del documento

## Recuperación

Producción debe combinar:

1. Búsqueda vectorial para similitud semántica.
2. Búsqueda léxica para cifras, medicamentos y términos exactos.
3. Filtros obligatorios de población y ámbito.
4. Reranking de los 20 candidatos.
5. Umbral calibrado; debajo del umbral, abstención.

El adaptador `InMemoryRetriever` prueba el contrato, no la calidad clínica.
`backend/schema.sql` define tablas e índices para pgvector.

## Generación

El prompt en `backend/prompts/base.py` exige:

- usar solo fragmentos recuperados;
- indicar insuficiencia;
- priorizar signos de alarma;
- citar documento y página;
- no inventar dosis ni contraindicaciones.

Antes de mostrar la respuesta, un verificador debe dividirla en afirmaciones y
comprobar que cada una esté respaldada por al menos un fragmento.

## API

`POST /v1/query`

```json
{
  "query": "Paciente con...",
  "disease_ids": ["hypertension"],
  "source_types": ["GPC"],
  "top_k": 5
}
```

La respuesta incluye resumen, fuentes, certeza, abstención y flags de
seguridad. `POST /v1/documents` queda bloqueado hasta integrar almacenamiento,
antivirus, cola de ingesta y permisos.

