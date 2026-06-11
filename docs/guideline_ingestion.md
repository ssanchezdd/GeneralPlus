# Ingesta de guías clínicas

## Estado actual

El pipeline ya ejecuta de extremo a extremo la fase previa a indexación:

```text
manifiesto
  -> descarga HTTPS desde dominio oficial
  -> validación de MIME, firma PDF, tamaño, páginas y SHA-256
  -> rechazo de PDF cifrado o con acciones, JavaScript o adjuntos
  -> extracción con trazabilidad por página
  -> limpieza de encabezados, pies, paginación e hifenación
  -> segmentación por secciones clínicas
  -> JSONL con metadatos
  -> informe de revisión
  -> aprobación clínica obligatoria
  -> embeddings OpenAI de 1536 dimensiones
  -> PostgreSQL + pgvector
```

La descarga y preparación están habilitadas. La indexación está bloqueada
intencionalmente porque las dos guías tienen
`clinical_review_status: "pending"`.

## Archivos de control

- `data/guidelines_manifest.json`: fuentes candidatas, prioridad, alcance y
  estado de revisión clínica.
- `data/guidelines_lock.json`: URL final, SHA-256, tamaño, ETag y fecha de
  descarga observados.
- `data/guideline_priorities.json`: cola clínica priorizada.
- `data/ingestion_reports/summary.json`: resultados técnicos versionados.
- `data/raw_guidelines/`: PDFs locales, excluidos de Git.
- `data/processed_chunks/`: JSONL locales, excluidos de Git.
- `data/ingestion_reports/<id>.json`: informes completos locales.

No se reemplaza un PDF, un JSONL ni una versión indexada sin `--force`. Cuando
se fuerza una descarga, la copia anterior se conserva en `.versions`.

## Preparación

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe ingest_guidelines.py `
  --manifest data\guidelines_manifest.json `
  --prepare-only
```

Para preparar una sola guía:

```powershell
.\.venv\Scripts\python.exe ingest_guidelines.py `
  --prepare-only `
  --id col-gpc-hta-2017-profesionales
```

## Indexación

La promoción exige simultáneamente:

1. `clinical_review_status: "approved"`.
2. Identidad y fecha del revisor en el manifiesto.
3. Cero banderas pendientes en el informe de ingesta.
4. `OPENAI_API_KEY` y `DATABASE_URL`.

```powershell
docker compose up -d pgvector
$env:DATABASE_URL = "postgresql://criterio:criterio-local-only@127.0.0.1:5432/criterio"
$env:OPENAI_API_KEY = "..."
.\.venv\Scripts\python.exe ingest_guidelines.py --init-schema
```

El proveedor de embeddings valida cantidad y dimensión de cada lote. El
repositorio hace el reemplazo documental y de chunks en una transacción.

## Metadatos de cada chunk

Cada registro conserva:

- guía, título, condición, editorial, país, año y tipo de fuente;
- página inicial/final y encabezado;
- sección clínica y tipo de recomendación inferidos;
- población, nivel de atención y urgencia;
- elegibilidad para recuperación;
- URL oficial y SHA-256 del PDF;
- contenido y estimación de tokens.

El objetivo es 700 a 1200 tokens, con 120 tokens de solapamiento. Los bloques
generales y metodológicos se conservan para auditoría, pero no participan por
defecto en recuperación.

## Validación de recuperación

```powershell
.\.venv\Scripts\python.exe test_retrieval.py `
  --query "manejo inicial de hipertensión arterial en primer nivel"
```

El validador local no reemplaza los embeddings. Sirve para comprobar
segmentación, inferencia conservadora de HTA/DM2, filtros, páginas, citas y
abstención sin enviar contenido a un proveedor externo.

## Resultado del 11 de junio de 2026

| Guía | Páginas | Chunks | Recuperables | Resultado técnico |
| --- | ---: | ---: | ---: | --- |
| HTA 2017 | 32 | 12 | 9 | 702–874 tokens; revisión clínica pendiente |
| DM2 2016 | 606 | 248 | 148 | 1 página vacía, 28 avisos de rotación y 2 chunks cortos |

Los dos hashes coinciden con el manifiesto y no se detectó contenido activo.
HTA cumple completamente el rango objetivo. DM2 tiene promedio de 872 tokens
y dos excepciones de 545 a 699 tokens; no puede promoverse hasta revisar las
páginas afectadas y resolver sus banderas.
