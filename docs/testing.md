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

- chunking con páginas y tamaño;
- abstención sin evidencia;
- fuente y página en consultas con coincidencia;
- flag de seguridad para dolor torácico.

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
| Python unittest | 4/4 pruebas |
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
py -m unittest discover -s backend/tests
```

## Pruebas médicas pendientes

Las pruebas unitarias no validan contenido clínico. Antes de un piloto:

- 50 casos frecuentes con respuesta esperada;
- 20 casos de bloqueo por alta criticidad;
- revisión de cita por afirmación;
- medición de omisiones críticas;
- prueba de consultas ambiguas y fuera de alcance;
- evaluación por al menos dos médicos independientes.
