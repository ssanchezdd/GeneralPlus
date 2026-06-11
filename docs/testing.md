# Pruebas

## Automatización incluida

### Frontend y motor local

`lib/clinical-engine.test.ts` verifica:

- normalización de tildes;
- recuperación de HTA para el caso de referencia;
- alerta tiempo-dependiente por dolor torácico;
- detección de ITU complicada;
- abstención ante pregunta fuera del corpus;
- límite de alcance de HTA y evaluación prioritaria.

### Backend

`backend/tests/test_backend.py` verifica:

- contrato API, modo de recuperación y citas formateadas;
- validación de manifiesto, dominio oficial y revisor;
- descarga PDF y protección contra sobrescritura;
- limpieza, chunking clínico, páginas y tamaño;
- recuperación local con filtros;
- bloqueo de indexación pendiente;
- abstención exacta, fuentes y flags tiempo-dependientes.

### Build

`scripts/verify-build.mjs` exige:

- `out/index.html`;
- `out/404.html`;
- marca del producto;
- disclaimer de juicio clínico.

## Resultado del corte

Ejecutado el **11 de junio de 2026**:

| Control | Resultado |
| --- | --- |
| ESLint | Aprobado, 0 errores |
| TypeScript estricto | Aprobado |
| Vitest | 6/6 pruebas |
| Python unittest | 17/17 pruebas |
| Preparación de PDFs oficiales | 2/2 hashes y conteos de página aprobados |
| Recuperación local | HTA, DM2 y abstención aprobadas |
| pgvector | Extensión 0.8.2, esquema y distancia coseno aprobados |
| Auditoría npm | 0 vulnerabilidades conocidas |
| Next.js producción | 3 páginas estáticas generadas |
| Verificación del artefacto | `index.html` y `404.html` aprobados |
| Simulación de Pages | Base path `/GeneralPlus` aprobado |
| GitHub Actions | Build y deploy aprobados |
| Verificación pública HTTPS | HTTP 200, título y disclaimer presentes |

## Comandos

```powershell
npm run lint
npm run typecheck
npm test
npm run build
npm run verify:build
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe scripts\smoke_pgvector.py
docker compose config --quiet
```

## Pruebas médicas pendientes

Las pruebas unitarias no validan contenido clínico. Antes de un piloto:

- 50 casos frecuentes con respuesta esperada;
- 20 casos de bloqueo por alta criticidad;
- revisión de cita por afirmación;
- medición de omisiones críticas;
- prueba de consultas ambiguas y fuera de alcance;
- evaluación por al menos dos médicos independientes.
