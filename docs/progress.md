# Avances y decisiones

Fecha de corte: **11 de junio de 2026**.

## Resumen ejecutivo

El MVP web continúa publicado en GitHub Pages y ahora cuenta con un pipeline
ejecutable de curación de guías. Dos documentos oficiales fueron descargados,
fijados por hash, extraídos y segmentados. La promoción a embeddings y
pgvector permanece bloqueada hasta aprobación clínica real.

## Publicación

- Repositorio: <https://github.com/ssanchezdd/GeneralPlus>
- Aplicación: <https://ssanchezdd.github.io/GeneralPlus/>
- Rama: `main`
- Despliegue: GitHub Actions + GitHub Pages, HTTPS obligatorio
- Primer commit funcional: `f3e546e`
- Workflow validado: `Deploy GP Colombia to Pages`

La URL pública respondió HTTP 200 y se verificaron en el HTML la marca
`Criterio` y el disclaimer clínico.

## Avance por semana del plan

| Semana | Estado | Entregable |
| --- | --- | --- |
| 1. Diseño | Completa para MVP | Especificación, taxonomía, fuentes y seguridad. |
| 2. Ingesta RAG | Completa técnicamente | Manifiesto, lock, descarga segura, extracción, chunking, embeddings y pgvector. |
| 3. Chat clínico | Completa para demo | Recuperación local, respuesta estructurada y citas. |
| 4. Checklists | Completa para demo | Checklists, error detector y exportación de borrador. |
| 5. Evaluación médica | Parcial | Pruebas técnicas; faltan 50 casos y revisión clínica. |
| 6. MVP usable | Parcial | UI web y Pages; faltan login, historial y backend alojado. |

## Decisiones técnicas

### Exportación estática

GitHub Pages solo sirve archivos estáticos. Next.js usa `output: "export"` y
calcula `basePath` desde `GITHUB_REPOSITORY`. FastAPI y PostgreSQL deben
alojarse en otro servicio cuando se active el RAG real.

### Corpus local curado

La demo web sigue usando fragmentos estructurados para no aparentar una
validación clínica inexistente. En paralelo, el corpus de preparación ya
contiene HTA 2017 y DM2 2016, con 260 chunks en total. Los archivos procesados
no se publican en Pages y no se indexan mientras su revisión esté pendiente.

### Promoción controlada

La indexación exige aprobación clínica, revisor, fecha y cero banderas
técnicas. HTA no presenta banderas técnicas. DM2 requiere revisar una página
clínica vacía, 28 avisos de texto rotado y dos chunks cortos.

### Abstención

Una consulta sin score suficiente devuelve evidencia insuficiente. Esta
conducta es parte del producto, no un error técnico.

### Fuente y alcance

La UI no solo muestra la cita: muestra para qué población y escenario sirve.
La exclusión de urgencias en la GPC de HTA se trata como dato operacional.

## Archivos principales

- `components/clinical-copilot.tsx`: interfaz y cuatro módulos.
- `lib/clinical-engine.ts`: recuperación, alertas, abstención y exportación.
- `data/evidence_chunks.json`: corpus demostrativo.
- `data/guidelines_manifest.json`: catálogo curado y control de aprobación.
- `backend/ingest/runner.py`: orquestación de ingesta.
- `backend/schema.sql`: modelo pgvector y auditoría.
- `docs/guideline_ingestion.md`: operación y resultados del pipeline.
- `.github/workflows/pages.yml`: CI y Pages.

## Pendientes antes de piloto

- Validación médica formal y gestión de vigencia documental.
- Revisión clínica formal de HTA y DM2.
- Resolver las banderas técnicas de DM2.
- Ampliar el corpus según `data/guideline_priorities.json`.
- Añadir reranking y verificación afirmación-cita.
- Backend alojado, autenticación, auditoría y privacidad.
- Evaluación de seguridad con casos adversariales.
- Revisión legal, regulatoria y de seguridad de la información.
