# Seguridad médica

## Clasificación

Criterio es software de apoyo a la decisión clínica. El equipo legal y
regulatorio debe determinar su clasificación antes de uso real. El MVP no debe
recibir información identificable ni utilizarse para decidir atención.

## Barreras implementadas

- Disclaimer persistente y estado de prototipo visible.
- Alertas separadas para dolor torácico, riesgo suicida y alarma obstétrica.
- Detección de TA elevada con síntomas y advertencia de alcance.
- Abstención cuando el score local es insuficiente.
- Enlaces directos a fuente y página.
- Certeza del sistema separada de fuerza de recomendación.
- Detector de errores basado en reglas legibles.

## Hallazgo de alcance relevante

La GPC colombiana de hipertensión arterial primaria, actualización parcial de
2017, declara que la urgencia hipertensiva y la hipertensión del embarazo están
fuera de su alcance. El producto no debe extrapolar sus recomendaciones a esos
escenarios. Esta restricción está representada en datos, UI y pruebas.

## Riesgos pendientes

| Riesgo | Control requerido |
| --- | --- |
| Guía desactualizada | Registro de vigencia, revisión clínica y fecha de próxima evaluación. |
| Cita correcta pero insuficiente | Verificador afirmación-cita y revisión por pares. |
| Omisión de red flag | Conjunto de bloqueo y evaluación adversarial por especialidad. |
| Sesgo por corpus incompleto | Cobertura visible, abstención y filtros de población. |
| Automatización excesiva | No preseleccionar órdenes ni firmar notas automáticamente. |
| Exposición de datos | Cifrado, minimización, retención definida y control de acceso. |

## Revisión de fuentes

Cada documento debe registrar:

- URL oficial, hash SHA-256 y fecha de descarga.
- Año, versión, institución y estado de vigencia.
- Población incluida y excluida.
- Fuerza de recomendación y calidad de evidencia cuando estén disponibles.
- Revisor clínico, fecha, decisión y conflictos de interés.

## Evaluación clínica propuesta

1. Crear 50 casos frecuentes y 20 casos de bloqueo por alta criticidad.
2. Obtener respuesta esperada de dos médicos independientes.
3. Medir omisión crítica, conducta peligrosa, cita incorrecta y abstención.
4. Resolver desacuerdos por consenso.
5. Congelar corpus, prompts y versión antes de cada ronda.

## Respuesta a eventos críticos

Una señal de alta criticidad debe producir un bloque corto y visible que
indique activación de la ruta local. El texto generado nunca debe retrasar la
atención. Los números de emergencia y rutas específicas deben parametrizarse
por territorio e institución, no codificarse sin validación operativa.

