# Especificación de producto

## Problema

En consulta general, el médico debe integrar síntomas, signos de alarma,
documentación, rutas de remisión y fuentes dispersas. Una respuesta fluida sin
trazabilidad puede aumentar el riesgo. Criterio prioriza la fuente y muestra el
límite de la evidencia recuperada.

## Usuarios

- Médico general en consulta ambulatoria colombiana.
- Auditor o líder de calidad que revisa documentación y remisiones.
- Equipo médico que valida contenido antes de publicarlo.

## Propuesta

Ante una pregunta clínica, el sistema:

1. Detecta señales de alta criticidad antes de ejecutar el RAG.
2. Recupera fragmentos con filtros clínicos y administrativos.
3. Responde solo con contenido sustentado.
4. Muestra documento, institución, año, página, alcance y certeza.
5. Se abstiene cuando no hay evidencia suficiente.
6. Produce un borrador revisable, nunca una orden automática.

## Alcance del MVP

Implementado:

- Consulta con seis fragmentos curados.
- HTA, SCA, salud mental, embarazo, EPOC y RIAS.
- Checklists, detector de errores y biblioteca.
- Respuesta estructurada y copia de borrador.
- Diseño adaptable a escritorio y móvil.
- Exportación estática y despliegue automatizado.

Fuera del MVP estático:

- Historias clínicas reales o datos identificables.
- Login, roles, auditoría y persistencia de consultas.
- Carga real de PDF desde el navegador.
- Embeddings, pgvector y generación con LLM en producción.
- Validación prospectiva por un comité médico.
- Integración con HCE, MIPRES, RIPS o redes de prestación.

## Requisitos funcionales de producción

| ID | Requisito | Criterio |
| --- | --- | --- |
| F-01 | Citas obligatorias | Toda afirmación clínica enlaza uno o más fragmentos. |
| F-02 | Abstención | Score insuficiente produce una respuesta sin recomendación. |
| F-03 | Alcance | La respuesta indica población y escenarios excluidos por la fuente. |
| F-04 | Seguridad | Las alertas tiempo-dependientes aparecen antes del texto generado. |
| F-05 | Trazabilidad | Se guarda versión de documento, chunks y configuración del modelo. |
| F-06 | Feedback | El médico reporta omisión crítica o cita incorrecta. |

## Métricas de salida a piloto

- 0 omisiones críticas en el conjunto de bloqueo.
- 100 % de afirmaciones clínicas con cita válida.
- Menos de 2 % de citas que no soportan la afirmación.
- Abstención mayor a 95 % en preguntas fuera del corpus.
- Revisión médica independiente de cada fuente y plantilla.
- P95 menor a 5 segundos en consulta no urgente.

