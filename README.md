# NTC Agent Router

Skill de NeaTech para decidir cuándo delegar trabajo y qué modelo y esfuerzo
usar en cada subtarea. Funciona con los agentes nativos de Codex y Claude Code.

Una corrección pequeña se resuelve en el agente principal. Dos módulos
independientes pueden trabajarse en paralelo. Un diagnóstico con evidencia
contradictoria puede necesitar más razonamiento y una revisión. El router toma
esas decisiones según la tarea y los controles disponibles en la sesión.

## Instalación

Requiere Python 3.11 o posterior solo para instalar. La skill no necesita
dependencias, claves API ni un proceso en segundo plano.

```sh
git clone https://github.com/ntc-ar/ntc-agent-router.git
cd ntc-agent-router
python install.py --target all --dry-run
python install.py --target all
```

En Windows también podés usar `py -3` en lugar de `python`. Para instalar en una
sola herramienta, elegí `--target codex` o `--target claude`.

| Destino | Archivos |
| --- | --- |
| Codex | `~/.codex/skills/ntc-agent-router/` |
| Claude Code | `~/.claude/skills/ntc-agent-router/` y `~/.claude/agents/ntc-effort-*.md` |

El instalador respeta `CODEX_HOME` y `CLAUDE_CONFIG_DIR`. `--home RUTA` permite
probar con otro directorio de usuario e ignora esas variables. Si tu distribución
de Codex descubre skills en `~/.agents/skills`, podés copiar allí la carpeta
`skills/ntc-agent-router`; evitá mantener dos copias con el mismo nombre.

Una reinstalación conserva una copia de los archivos reemplazados en
`backups/ntc-agent-router/` dentro del directorio de configuración de cada
herramienta. Los archivos idénticos se dejan como están. Si falla un reemplazo,
el instalador intenta restaurar los destinos anteriores y conserva los backups.
No modifica la configuración, autenticación ni instrucciones generales.

Abrí una sesión nueva después de instalar, especialmente en Claude Code, para
cargar los perfiles. Codex puede detectar cambios automáticamente; si la skill
no aparece en el selector, reiniciá la aplicación.

## Uso

En Codex:

```text
$ntc-agent-router status
$ntc-agent-router Revisá este proyecto y corregí los errores que encuentres.
$ntc-agent-router economy Compará estos registros y devolvé las diferencias.
$ntc-agent-router quality Investigá esta condición de carrera.
```

En Claude Code:

```text
/ntc-agent-router status
/ntc-agent-router Revisá este proyecto y corregí los errores que encuentres.
```

También puede activarse automáticamente cuando corresponde delegar. `status`
informa qué puede controlar sin lanzar agentes de prueba. `off` deja de aplicar
esta política en la conversación.

Podés ajustar el criterio en lenguaje natural:

```text
Usá como máximo dos agentes, priorizá tiempo y elegí el esfuerzo en cada caso.
Mantené este modelo para todos los agentes, con esfuerzo automático hasta high.
Delegá la documentación y encargate de la implementación principal.
```

## Cómo decide

El router separa tres decisiones: qué parte del trabajo es independiente, qué
capacidad de modelo necesita y cuánto razonamiento conviene dedicarle.
Considera incertidumbre, dependencias, consecuencias de un error y facilidad de
verificación. El tamaño de un archivo no determina por sí solo la dificultad.

Los roles se asignan según el trabajo. No hay una lista fija de modelos ni una
asociación permanente entre modelo y esfuerzo. Los agentes pueden implementar
cambios autorizados con archivos asignados, además de investigar o revisar.

En Codex hay una preferencia deliberada por **GPT-5.3-Codex-Spark para el grueso
de la implementación**, cuando está disponible y el trabajo puede acotarse.
El principal define interfaces, integra y revisa; Spark produce código por
partes coherentes, con pruebas indicadas en el encargo. Su esfuerzo también se
decide por subtarea. Una primera versión puede necesitar correcciones, pero el
resultado final debe pasar las mismas verificaciones.

Esta preferencia permite aprovechar una cuota separada cuando la cuenta la
ofrece. El router consulta los límites nativos si están expuestos; no presupone
acceso ni cuota ilimitada. La coordinación y las correcciones pueden consumir
el cupo principal. Si Spark no está disponible o el retrabajo deja de compensar,
elige otra ruta. Podés pedir «sin preferencia por Spark» o elegir otro modelo.

El modo predeterminado es `auto`. `economy` favorece menos llamadas y reutilizar
resultados; `balanced` equilibra calidad y tiempo; `quality` permite profundizar
o sumar una revisión útil. Ningún modo obliga a crear agentes ni a usar siempre
el modelo más grande.

Sin un límite indicado por el usuario, la política permite cuatro intentos de
agente por tarea, incluidos reintentos y continuaciones. La concurrencia se
decide con las subtareas listas y los lugares libres del entorno. Estos límites
son instrucciones; no son un tope de facturación impuesto por el programa.

## Diferencias entre herramientas

**Codex:** usa los parámetros de modelo y esfuerzo expuestos por su herramienta
de agentes. Si el entorno requiere contexto separado para cambiar esos valores,
envía un encargo autocontenido. No instala perfiles con modelos fijos.

**Claude Code:** puede seleccionar modelo por llamada. Para las versiones que
configuran esfuerzo mediante frontmatter, incluye cinco perfiles de esfuerzo:
`low`, `medium`, `high`, `xhigh` y `max`. El router elige el perfil al delegar y
selecciona el modelo por separado. Solo usa combinaciones compatibles con el
modelo y la versión en ejecución. Los perfiles heredan herramientas y permisos.

El modelo principal y su esfuerzo permanecen como los configuraste. Las
preferencias o variables del entorno pueden prevalecer sobre una solicitud del
router; la skill distingue lo solicitado de lo confirmado por el runtime.

**ChatGPT web:** el archivo de skill puede orientar decisiones si la interfaz
permite cargarlo. No instala agentes locales ni habilita controles que esa
interfaz no exponga. La versión local se verifica por separado.

## Verificación

```sh
python -m unittest discover -s tests -v
```

Las pruebas comprueban instalación, reinstalación, backups y recuperación ante
errores en directorios temporales. No llaman a modelos. Los casos de decisión y
el alcance de las pruebas realizadas están en [VALIDATION.md](VALIDATION.md).

El router es una política ejecutada por el modelo. Las pruebas de archivos no
demuestran que siempre vaya a elegir bien, y no hay un porcentaje de ahorro
prometido. Para medirlo hay que comparar tareas equivalentes e incluir contexto,
coordinación, verificaciones y reintentos.

## Archivos

- `skills/ntc-agent-router/`: política común y adaptadores por herramienta.
- `claude-agents/`: perfiles nativos que permiten elegir esfuerzo en Claude Code.
- `install.py`: instalador para Windows, Linux y macOS.
- `tests/`: pruebas locales sin servicios externos.

Las referencias de cada adaptador enlazan la documentación oficial. Los
parámetros disponibles en la sesión tienen prioridad frente a cualquier ejemplo.

NeaTech · NTC
