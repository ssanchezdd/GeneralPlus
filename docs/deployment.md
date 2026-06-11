# Despliegue

## GitHub Pages

El workflow `.github/workflows/pages.yml`:

1. instala dependencias con `npm ci`;
2. instala las dependencias Python del backend;
3. ejecuta lint, tipos, pruebas web y pruebas backend;
4. genera el export estático;
5. valida el artefacto;
6. publica `out/` con las acciones oficiales de Pages.

Permisos requeridos:

- `contents: read`
- `pages: write`
- `id-token: write`

El repositorio debe configurar **Settings > Pages > Source: GitHub Actions**.

## Base path

`next.config.ts` detecta repositorios de proyecto y usa
`/<nombre-repositorio>` como `basePath`. Para un repositorio
`usuario.github.io`, deja la raíz vacía.

## Backend

GitHub Pages no ejecuta FastAPI ni PostgreSQL. En producción:

- despliegue el backend en un servicio con red privada a PostgreSQL;
- limite CORS al dominio publicado;
- use secretos del proveedor, no variables públicas de Next.js;
- añada almacenamiento de documentos, antivirus y cola de trabajos;
- aplique migraciones desde `backend/schema.sql`;
- configure observabilidad sin registrar texto clínico identificable.

## Rollback

Pages conserva deployments en GitHub Actions. Un rollback debe hacerse
revirtiendo a un commit validado y ejecutando nuevamente el workflow, de modo
que código, corpus y documentación queden versionados juntos.
