# Validación

Revisión inicial: 4 de septiembre de 2026.

## Evaluación del diseño

El kit original servía como política de delegación. Sus comprobaciones de
capacidad y su distinción entre modelo solicitado y confirmado eran útiles.
La selección quedaba limitada por cuatro combinaciones fijas de modelo y
esfuerzo, agentes exclusivamente de lectura y soporte solo para OpenAI.

Esta versión conserva la comprobación de capacidades y cambia la selección por
una política por subtarea. Los agentes pueden implementar cambios con alcance
definido. Codex tiene una preferencia por Spark para implementación verificable;
Claude Code usa perfiles de esfuerzo que permiten elegir el modelo por separado.
La preferencia por Spark puede desactivarse y no obliga a usar un modelo ausente.

## Comprobaciones realizadas

- Validación de frontmatter y metadatos de la skill.
- Validación YAML de los cinco perfiles Claude y de sus niveles de esfuerzo.
- Trece pruebas del instalador con Python 3.14 en Windows, sin errores ni pruebas
  omitidas: instalación, reinstalación, conservación de archivos ajenos,
  idempotencia, backups, fallos de copia y reemplazo, y rechazo de enlaces.
- Instalación real en ambas herramientas y segunda ejecución sin cambios.
- Descubrimiento nativo en Codex CLI 0.153.1 mediante `skills/list`: una skill
  de usuario habilitada, sin duplicados.
- Delegación nativa solicitando Luna con esfuerzo low para extraer los cinco
  perfiles; el resultado coincide con los archivos.
- Implementación nativa solicitando GPT-5.3-Codex-Spark con esfuerzo medium:
  workflow de CI y ajuste de los tests para directorios temporales de macOS.
  Cambios revisados y trece pruebas superadas.

Las dos delegaciones comprobaron ejecución y resultado. El control usado
aceptó modelo y esfuerzo solicitados, pero no devolvió metadatos que permitan
afirmar de forma independiente cuáles fueron los valores efectivos.

El workflow de GitHub ejecuta las pruebas con Python 3.11 en Windows, Linux y
macOS. El resultado de cada revisión se puede consultar en Actions.

## Casos de decisión

Se realizó una evaluación de instrucciones con escenarios simulados, además
de las comprobaciones de ejecución anteriores. No es un benchmark.

| Situación | Comportamiento revisado |
| --- | --- |
| Reemplazo exacto de una palabra | Resolver en el principal, sin crear agentes |
| Dos módulos independientes | Delegar uno, asignar archivos y avanzar con el otro |
| Modelo que ofrece low/high pero no medium | Elegir un nivel admitido que cubra la dificultad |
| Evidencia esencial sin acceso | Identificar el bloqueo; más esfuerzo no da permisos |
| Modelo y esfuerzo elegidos exactamente, combinación no soportada | Informar el bloqueo sin sustituirlos |
| Dos intentos permitidos, uno completado y uno fallido | Terminar localmente dentro de las restricciones |
| Claude sin esfuerzo por llamada | Elegir un perfil compatible, sin inventar parámetros |
| Modelo impuesto por el entorno | Diferenciar solicitud y configuración efectiva |
| Spark disponible para implementación acotada | Priorizarlo y revisar el código resultante |
| Spark agotado o con errores reiterados | Corregir la causa o elegir otra ruta dentro del presupuesto |

La evaluación detectó ambigüedades al heredar esfuerzo o volver al principal.
Se ajustó la política para que esos caminos respeten siempre las elecciones
exactas y los límites del usuario, incluso cuando no permiten terminar la tarea.

## Límites de esta validación

Claude Code 2.1.195 estaba instalado sin autenticación activa. Se verificaron
los archivos, los campos aceptados localmente y la instalación; queda pendiente
ejecutar los perfiles en una sesión autenticada de Claude Code.

La detección de skills no prueba por sí sola la selección automática en toda
conversación. Tampoco se midió ahorro de dinero, tokens ni cuota. La calidad del
routing debe seguir evaluándose con trabajo real y verificaciones de resultado.
