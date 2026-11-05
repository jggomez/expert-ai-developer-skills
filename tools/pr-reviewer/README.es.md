# pr-reviewer

Una GitHub Action que revisa los pull requests en seguridad, rendimiento, escalabilidad, diseño, buenas
prácticas y coste. Solo comenta y nunca bloquea el merge.

[Read in English](README.md)

## Qué revisa

| Eje | Ejemplos |
| --- | --- |
| Seguridad | Riesgos del OWASP Top 10: control de acceso roto, inyección, XSS, SSRF, autenticación débil, secretos expuestos |
| Rendimiento | Consultas N+1, I/O en bucles, complejidad evitable, bloqueos en código async |
| Escalabilidad | Memoria sin límite, falta de paginación o timeouts, estado en un solo proceso, condiciones de carrera |
| Diseño | Problemas SOLID con daño concreto, lógica duplicada, abstracciones innecesarias |
| Buenas prácticas | Errores silenciados, transacciones ausentes, floats para dinero, cambios de API incompatibles |
| Coste | APIs de pago en bucles, `SELECT *` en almacenes de datos facturados, reintentos sin tope, prompts de LLM enormes, logs excesivos |

Quedan fuera el estilo, los nombres y los tests que falten. Cada hallazgo necesita una línea del diff, un
impacto y un nivel de confianza. Un PR limpio recibe solo un resumen breve de "sin problemas".

Es una revisión con IA, no una auditoría de seguridad: puede pasar por alto vulnerabilidades, así que mantén
tus escáneres. En un repo público sus comentarios también son públicos, así que atiende un hallazgo grave antes
de que el PR se difunda.

## Proveedores

| | Antigravity | Claude Managed Agents |
| --- | --- | --- |
| Dónde corre el agente | Tu runner de GitHub | Un sandbox alojado por Anthropic, sin red |
| Qué puede leer | Todo el repositorio (copia limpia) | El diff y los archivos cambiados |
| Modelo por defecto | `gemini-3.8-flash` | `claude-opus-5-5` |
| Tope de gasto | Tokens, con `max-tokens` | Dólares, con `budget-usd` |
| Coste en el resumen | Estimado con precios de lista | Informado por la API, con tiempo de sesión |
| Estado | SDK 0.1.x | API en beta |

## Instalación

1. Guarda una [clave de API de Gemini](https://aistudio.google.com/apikey) como el secreto `GEMINI_API_KEY` del
   repositorio.
2. Copia [`examples/pr-review.yml`](examples/pr-review.yml) a `.github/workflows/pr-review.yml`.
3. Sustituye `<commit-sha>` por un SHA completo de este repositorio y abre un pull request.

Para repetir la revisión en un PR, un owner, member o collaborator comenta `/review`.

La **[guía](docs/guide.es.md)** explica cada paso, Claude, toda la configuración, el prompt y la solución de
problemas.

> [!WARNING]
> Con la capa gratuita de la API de Gemini, Google puede usar tu código para mejorar sus productos, y revisores
> humanos pueden leerlo. Usa una clave de pago o Vertex AI para cualquier código privado. Consulta los
> [términos de la API de Gemini](https://aistudio.google.com/docs/terms).

## Entradas

Todas son opcionales excepto la clave. Cada una acepta también una variable `PR_REVIEW_*`, listadas en la
[guía](docs/guide.es.md#cambiar-la-configuración), y el workflow de ejemplo lee variables del repositorio, así que
puedes cambiar el modelo sin editar ningún archivo.

| Entrada | Por defecto | Descripción |
| --- | --- | --- |
| `api-key` | | Clave de API de Gemini o de Anthropic |
| `provider` | `antigravity` | `antigravity`, `claude`, o `fake` para probar la instalación sin IA ni clave |
| `model` | El del proveedor | Modelo que se usa |
| `max-tokens` | `200000` | Tope de tokens por revisión (Antigravity) |
| `budget-usd` | `1.00` | Tope de gasto por revisión (Claude) |
| `claude-agent-id` | | Lo imprime `pr-reviewer setup-claude` |
| `claude-environment-id` | | Lo imprime `pr-reviewer setup-claude` |
| `max-findings` | `10` | Máximo de hallazgos publicados |
| `min-severity` | `low` | Severidad mínima que se publica: `critical`, `high`, `medium` o `low` |
| `exclude` | | Patrones de rutas adicionales que se omiten, separados por comas o saltos de línea |
| `max-diff-chars` | Límite interno | Tamaño máximo del diff |
| `rubric-file` | | Archivo Markdown que sustituye los criterios, leído del commit base. Consulta [Cambiar el prompt](docs/guide.es.md#cambiar-el-prompt) |
| `instructions` | | Texto que se añade a los criterios |
| `github-token` | `github.token` | Token que lee el PR y publica comentarios. Mantén el valor por defecto: las ejecuciones repetidas reconocen los comentarios anteriores por su autor bot |

Se omiten por defecto los lockfiles, el código generado, los artefactos de compilación y el código vendorizado.
En diffs grandes se priorizan los archivos fuente, y el resumen lista todo lo que no se revisó.

## Coste

Cada revisión está limitada por `max-tokens`, y el resumen informa los tokens y el coste estimado. Como guía
aproximada y sin medir, una revisión de 40k tokens de entrada y 4k de salida cuesta unos $0.05 con
`gemini-3.8-flash`, $0.12 con `claude-sonnet-5-5` y $0.24 con `claude-opus-5-5`, más el tiempo de sesión en
Claude. Se ejecuta al abrir un PR o marcarlo como listo, y con `/review`, no en cada push.

## Limitaciones

- Se omiten los PR de forks y de Dependabot, porque sus ejecuciones no tienen acceso a secretos.
- Si falla la IA, el resumen lo indica y el job queda en verde.
- El SDK está en la versión 0.1.x, así que la versión va fijada y puede necesitar actualizaciones.

## Seguridad

Quien abre un PR controla el texto que lee el agente, por lo que ese texto se trata como hostil.

- El agente solo tiene herramientas de lectura: sin shell, red, escritura ni subagentes.
- Lee una copia limpia del repositorio, sin `AGENTS.md`, `GEMINI.md`, `.agents/`, `.git` ni symlinks.
- Con Claude no se monta ningún repositorio, porque un repo montado carga su `.claude/skills` sin revisión.
- El paso de revisión solo tiene la clave de IA y el de publicación solo tiene el token de GitHub.
- Los hallazgos se validan contra el diff, y se eliminan secretos, menciones, imágenes y HTML antes de publicar.
- Un `rubric-file` personalizado se lee del commit base, así que un PR no puede reescribir su propia revisión.
- Fija esta Action a un SHA de commit, como hace el ejemplo.

## Arquitectura

El código sigue clean architecture. Las dependencias solo apuntan hacia dentro, y
`tests/architecture` hace fallar la build si se rompe esa regla.

```text
src/pr_reviewer/
├── domain/        Reglas sin I/O: parseo del diff, selección de archivos, hallazgos, disparadores, precios
├── application/   Casos de uso (prepare_diff, run_review, publish_review), puertos, prompt, criterios
├── adapters/      Implementaciones de los puertos
│   ├── git/          Lee diffs
│   ├── github/       Cliente REST, renderizado Markdown, gateway del pull request
│   ├── filesystem/   Crea la copia limpia
│   └── providers/    Proveedores de revisión Antigravity, Claude y fake
└── entrypoints/   Línea de comandos y raíz de composición
```

Para añadir un proveedor, implementa el puerto `ReviewProvider` en `adapters/providers/` y regístralo en
`entrypoints/composition.py`. No cambia nada más.

## Desarrollo

```bash
cd tools/pr-reviewer
uv sync --extra dev --extra antigravity --extra claude
uv run pytest && uv run ruff check . && uv run mypy src
```

| Pruebas | Propósito | Requiere |
| --- | --- | --- |
| `tests/unit` | Reglas de dominio, casos de uso con puertos en memoria y renderizado Markdown | Nada |
| `tests/integration` | Adaptadores contra git, el sistema de archivos, una API de GitHub simulada y las clases reales del SDK | git, extras `antigravity` y `claude` |
| `tests/action` | Reglas de seguridad de `action.yml` y de los workflows | Nada |
| `tests/architecture` | Regla de dependencias entre capas | Nada |

Ninguna llama a una API de pago. Los datos compartidos de prueba están en `tests/support`.

Licencia Apache-2.0.
