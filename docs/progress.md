# Avances y decisiones

Fecha de corte: **11 de junio de 2026**.

## Resumen ejecutivo

Se partió de una carpeta sin código ni repositorio Git. Se construyó un MVP
funcional compatible con GitHub Pages y una base técnica separada para el RAG
de producción. La aplicación está orientada a demostrar interacción,
trazabilidad, abstención y seguridad; no a simular una validación médica que
todavía no existe.

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
| 2. Ingesta RAG | Base técnica | Chunker, pipeline por interfaces y esquema pgvector. |
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

La demo no llama un LLM ni internet. Usa seis fragmentos estructurados con
metadatos de alcance y reglas de recuperación deterministas. Esto permite
probar UX y fallos de seguridad sin afirmar que existe un sistema clínico
validado.

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
- `backend/schema.sql`: modelo pgvector y auditoría.
- `.github/workflows/pages.yml`: CI y Pages.

## Pendientes antes de piloto

- Validación médica formal y gestión de vigencia documental.
- Corpus completo con fuentes aprobadas y hashes.
- Recuperación híbrida y verificación afirmación-cita.
- Backend alojado, autenticación, auditoría y privacidad.
- Evaluación de seguridad con casos adversariales.
- Revisión legal, regulatoria y de seguridad de la información.
