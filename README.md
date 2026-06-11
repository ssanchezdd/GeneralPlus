# Criterio

Copiloto clínico colombiano con fuentes verificables, signos de alarma y
prevención de errores. Este repositorio convierte el plan de
`GeneralPlusPlan.txt` en un MVP estático desplegable en GitHub Pages y deja
definido el contrato técnico para un RAG de producción.

> **Estado:** prototipo para evaluación técnica y médica. No está validado para
> uso asistencial y no reemplaza el juicio clínico ni los protocolos
> institucionales.

## Qué incluye

- Consulta clínica con recuperación local, citas y abstención sin evidencia.
- Alertas para escenarios tiempo-dependientes y límites de alcance.
- Checklists interactivos por motivo de consulta.
- Detector transparente de errores clínicos frecuentes.
- Explorador de GPC y RIAS con enlaces oficiales.
- Exportación estática compatible con GitHub Pages.
- Contrato FastAPI, pipeline de ingesta y esquema PostgreSQL + pgvector.
- Manifiesto y lock de fuentes con SHA-256 y aprobación clínica obligatoria.
- Pruebas de recuperación, seguridad, chunking y build.

## Ejecutar localmente

```powershell
npm install
npm run dev
```

Validación completa:

```powershell
npm run lint
npm run typecheck
npm test
npm run build
npm run verify:build
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

El build estático queda en `out/`.

Preparación reproducible de guías:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe ingest_guidelines.py --prepare-only
```

La indexación real permanece bloqueada hasta que un revisor clínico apruebe
cada guía y se resuelvan todas las banderas técnicas.

## Estructura

```text
app/                  Next.js App Router y estilos
components/           Interfaz clínica
lib/                  Motor local de recuperación y seguridad
data/                 Taxonomías y fragmentos demostrativos
backend/              Contrato FastAPI, ingesta, RAG y pgvector
docs/                 Especificación, seguridad, arquitectura y avances
.github/workflows/    Validación y despliegue a GitHub Pages
```

## Documentación

- [Especificación de producto](docs/product_spec.md)
- [Seguridad médica](docs/medical_safety.md)
- [Pipeline RAG](docs/rag_pipeline.md)
- [Ingesta de guías](docs/guideline_ingestion.md)
- [Avances y decisiones](docs/progress.md)
- [Pruebas](docs/testing.md)
- [Despliegue](docs/deployment.md)

## Fuentes iniciales

Las fuentes curadas se mantienen en `data/guidelines_manifest.json` y sus
descargas quedan fijadas en `data/guidelines_lock.json`. El corpus preparado
usa dos GPC oficiales de MinSalud: HTA 2017 y DM2 2016. Ambas deben pasar por
revisión de vigencia y contenido clínico antes de indexarse.
