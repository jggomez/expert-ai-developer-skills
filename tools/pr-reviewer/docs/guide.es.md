# Guía de pr-reviewer

Instala el revisor en un repositorio y cambia lo que revisa.

## Qué necesitas

- Un repositorio de GitHub donde puedas añadir secretos y workflows.
- Una de estas opciones: una [clave de API de Gemini](https://aistudio.google.com/apikey), un plan Claude Pro o Max,
  o una [clave de API de Anthropic](https://platform.claude.com/settings/keys).

No se ejecuta nada en tu ordenador ni en un servidor tuyo. Las revisiones corren en runners de GitHub Actions.

## Instalar

### 1. Añadir el workflow

Desde la raíz de tu repositorio:

```bash
mkdir -p .github/workflows
SHA=$(git ls-remote https://github.com/jggomez/expert-ai-developer-skills refs/heads/main | cut -f1)
curl -fsSL https://raw.githubusercontent.com/jggomez/expert-ai-developer-skills/main/tools/pr-reviewer/examples/pr-review.yml \
  | sed "s/<commit-sha>/$SHA/" > .github/workflows/pr-review.yml
```

Esto copia [`examples/pr-review.yml`](../examples/pr-review.yml) y lo fija al último commit de este repositorio.
Para actualizar más adelante, ejecútalo otra vez y lee los cambios primero.

### 2. Conectar un proveedor

Sigue una opción. Los secretos y las variables están en tu repositorio, en
**Settings → Secrets and variables → Actions**, en las pestañas **Secrets** y **Variables**.

| Opción | Úsala cuando | Secreto | Variable `PR_REVIEW_PROVIDER` |
| --- | --- | --- | --- |
| [Gemini](#gemini) | Estás empezando | `GEMINI_API_KEY` | Ninguna |
| [Plan Claude Pro o Max](#plan-claude-pro-o-max) | El repositorio es tuyo y tienes un plan | `CLAUDE_CODE_OAUTH_TOKEN` | `claude-code` |
| [Clave de API de Anthropic](#clave-de-api-de-anthropic) | Sois un equipo o no tienes plan | `ANTHROPIC_API_KEY` | `claude-code` |
| [Claude Managed Agents](#claude-managed-agents) | Quieres un sandbox alojado y un tope en dólares | `ANTHROPIC_API_KEY` | `claude` |

#### Gemini

Crea una [clave](https://aistudio.google.com/apikey) y añádela como el secreto `GEMINI_API_KEY`.

#### Plan Claude Pro o Max

Las revisiones usan la [Claude Code Action](https://code.claude.com/docs/en/github-actions) oficial y cuentan contra
los límites de tu plan.

1. Crea un token en tu ordenador:

   ```bash
   claude setup-token
   ```

2. Añádelo como el secreto `CLAUDE_CODE_OAUTH_TOKEN`.
3. Añade la variable `PR_REVIEW_PROVIDER` con el valor `claude-code`.

El token pertenece a quien lo creó, así que nunca lo compartas ni lo pegues en un archivo. Los pull requests de
cualquier persona del repositorio usan los límites de quien lo creó. Si trabajan varias personas, usa una clave de API.

#### Clave de API de Anthropic

También usa la Claude Code Action, y se paga por tokens.

1. Crea una clave en la [Claude Console](https://platform.claude.com) y añádela como el secreto `ANTHROPIC_API_KEY`.
2. Añade la variable `PR_REVIEW_PROVIDER` con el valor `claude-code`.
3. No añadas `CLAUDE_CODE_OAUTH_TOKEN`. Si existe, se usa el token en vez de la clave.

Este camino tiene un límite de 20 turnos, pero no de dólares, así que fija un tope de gasto en la Console.

Las dos opciones de Claude Code revisan en una sola pasada, sin grupos, leen toda la copia limpia con herramientas de
solo lectura y no muestran un coste. El token de GitHub también llega a este paso, porque la Action oficial lo necesita.

#### Claude Managed Agents

Necesita un paso adicional, una sola vez, porque Managed Agents guarda el agente en tu cuenta de Anthropic. No queda
nada ejecutándose en tu ordenador.

1. Crea el agente, desde un clon de este repositorio:

   ```bash
   cd tools/pr-reviewer
   uv sync --extra claude
   export ANTHROPIC_API_KEY=tu_clave
   uv run pr-reviewer setup-claude
   ```

2. Añade el secreto `ANTHROPIC_API_KEY`.
3. Añade tres variables: `CLAUDE_AGENT_ID` y `CLAUDE_ENVIRONMENT_ID` con los ID impresos, y
   `PR_REVIEW_PROVIDER` con el valor `claude`.

Para volver a Gemini, borra `PR_REVIEW_PROVIDER`.

### 3. Hacer merge y probarlo

1. Haz commit de `.github/workflows/pr-review.yml` y llévalo a tu rama principal. Los comentarios `/review` solo
   funcionan desde ahí.
2. Abre un pull request, o cierra y reabre uno creado después de ese merge.
3. Mira los resultados como se explica abajo.

## Uso diario

**Cuándo corre.** Cuando un pull request se abre, se reabre o se marca como listo para revisión. No corre en cada push.

**Cómo revisar otra vez.** Escribe `/review` como un comentario normal en el pull request. Solo pueden usarlo owners,
members y collaborators. Los comentarios de otras personas se ignoran, así que un desconocido no puede gastar tu presupuesto.

**Dónde ver los resultados.**

- Los comentarios en línea aparecen en la pestaña **Files changed**.
- El resumen aparece en la pestaña **Conversation**, con el estado y, cuando están disponibles, el modelo, los tokens y el coste.
- La ejecución aparece en la pestaña **Actions**, en **AI PR review**.

Al ejecutarlo otra vez se actualiza el resumen y no se repiten los comentarios ya publicados.

**Quién paga.** El dueño de la clave o token guardado en el repositorio, sea quien sea el autor del pull request.

**Qué pull requests se revisan.** Los de ramas del mismo repositorio, de cualquier autor. Los de forks y de Dependabot
se omiten, porque GitHub no da acceso a secretos a esas ejecuciones.

**Un job en verde no significa una revisión limpia.** El job sigue en verde aunque la revisión falle, para no bloquear
nunca un merge. Lee el resumen.

## Cambiar la configuración

Un valor se puede fijar de tres formas. Gana la primera que se encuentre:

1. Un input bajo `with:` en el workflow.
2. Una variable de entorno `PR_REVIEW_*` en el workflow.
3. El valor por defecto.

El workflow de ejemplo conecta varios inputs con variables del repositorio, así que puedes cambiarlos en
**Settings → Secrets and variables → Actions → Variables** sin editar ningún archivo. Las variables que no existan
usan el valor por defecto. Para conectar otro input, añade una línea como
`max-tokens: ${{ vars.PR_REVIEW_MAX_TOKENS }}`.

| Input | Variable de entorno | Por defecto | Uso |
| --- | --- | --- | --- |
| `api-key` | | | Clave de Gemini o Anthropic, desde un secreto |
| `provider` | `PR_REVIEW_PROVIDER` | `antigravity` | `antigravity`, `claude` o `claude-code` |
| `model` | `PR_REVIEW_MODEL` | `gemini-3.6-flash` o `claude-opus-5-5` | Modelo que se usa |
| `max-shards` | `PR_REVIEW_MAX_SHARDS` | `4` | Máximo de grupos de un PR grande, revisados en paralelo |
| `fallback-model` | `PR_REVIEW_FALLBACK_MODEL` | `gemini-3.8-flash` | Modelo del último intento si el primero está saturado (Antigravity) |
| `max-tokens` | `PR_REVIEW_MAX_TOKENS` | `200000` | Tope de tokens por revisión (Antigravity) |
| `budget-usd` | `PR_REVIEW_BUDGET_USD` | `1.00` | Tope de gasto por revisión (Claude) |
| `max-findings` | `PR_REVIEW_MAX_FINDINGS` | `10` | Máximo de comentarios por revisión |
| `min-severity` | `PR_REVIEW_MIN_SEVERITY` | `low` | Severidad mínima que se publica |
| `exclude` | `PR_REVIEW_EXCLUDE` | | Patrones de rutas adicionales que se omiten |
| `max-diff-chars` | `PR_REVIEW_MAX_DIFF_CHARS` | Límite interno | Tamaño máximo del diff |
| `rubric-file` | `PR_REVIEW_RUBRIC_FILE` | | Archivo que sustituye los criterios |
| `instructions` | `PR_REVIEW_INSTRUCTIONS` | | Texto que se añade a los criterios |
| `claude-code-oauth-token` | `CLAUDE_CODE_OAUTH_TOKEN` | | Token para `provider: claude-code` |
| `claude-agent-id` | `CLAUDE_AGENT_ID` | | Lo da `setup-claude` |
| `claude-environment-id` | `CLAUDE_ENVIRONMENT_ID` | | Lo da `setup-claude` |
| `github-token` | | `github.token` | Mantén el valor por defecto |

Si eliges otro modelo con Antigravity, el coste estimado del resumen puede no ser correcto.

## Cambiar el prompt

**Añade reglas** con `instructions`. Se mantienen los criterios por defecto:

```yaml
instructions: |
  Todo el dinero usa Decimal.
  Cada endpoint bajo /admin necesita el decorador require_admin.
```

**Sustituye los criterios** con tu propio archivo:

1. Copia [`examples/pr-review-rubric.md`](../examples/pr-review-rubric.md) a `.github/pr-review-rubric.md`.
2. Edítalo y haz merge a tu rama por defecto.
3. Define `rubric-file: .github/pr-review-rubric.md`.

Se aplican tres reglas:

- **El archivo se lee del commit base.** Un pull request no puede cambiar su propia revisión, así que un cambio en
  este archivo aplica después del merge. Al revisar ese mismo PR se usa la versión anterior.
- **Los hallazgos usan seis categorías fijas:** `security`, `performance`, `scalability`, `design`, `best_practice`
  y `cost`. Los comentarios, el formato de salida y la validación dependen de ellas.
- **Las reglas de seguridad no se pueden quitar.** La instrucción de tratar el código como datos no confiables
  siempre se mantiene.

Si el archivo no existe, la revisión falla y el resumen dice por qué. No se usan los criterios por defecto en su
lugar. La rúbrica y las instrucciones tienen un límite de 20.000 caracteres cada una.

## Solución de problemas

| Qué ves | Qué significa | Qué hacer |
| --- | --- | --- |
| El job está en verde, pero no hay comentarios | El job sigue en verde aunque la revisión falle | Lee el comentario de resumen y el log del job |
| `HTTP 503` o `high demand` en el log | El modelo de Gemini está saturado. El revisor corta ese intento, reintenta y luego usa `fallback-model` | Nada, si la revisión termina. El resumen muestra el modelo usado |
| "No structured output after 3 attempts" | Fallaron todos los intentos, probablemente por la misma causa | Reabre el PR más tarde o elige otro `model` o `fallback-model` |
| `/review` no hace nada | El workflow no está en la rama por defecto, o el autor no tiene permiso | Haz merge del workflow. Solo pueden usarlo owners, members y collaborators |
| Se omite el PR de un fork | Las ejecuciones desde forks no acceden a secretos | Es lo esperado |
| La revisión ignora tu clave de API | `CLAUDE_CODE_OAUTH_TOKEN` existe y tiene prioridad | Borra ese secreto |
| Claude informa de un error de autenticación | El token o la clave caducó, se revocó o no está en el secreto | Crea uno nuevo y actualiza el secreto |
| `does not exist in the base commit` | La rúbrica aún no está en la rama destino | Haz merge de la rúbrica primero |

## Ejecutarlo en tu ordenador

Sirve para probar un cambio en el prompt sin abrir un PR:

```bash
cd tools/pr-reviewer
uv sync --extra antigravity
export GEMINI_API_KEY=tu_clave
uv run pr-reviewer diff --repo ../.. --base main --head HEAD --output /tmp/bundle.json
uv run pr-reviewer review --provider antigravity --repo ../.. --bundle /tmp/bundle.json \
  --workspace /tmp/pr-review-ws --output /tmp/report.json
```

Ejecuta `rm -rf /tmp/pr-review-ws` entre una ejecución y otra. Las variables `PR_REVIEW_*` también funcionan aquí.
Con `--rubric-file`, pasa también `--base` con un SHA completo. El resultado queda en `/tmp/report.json`: revisa
`status` y `error`, porque el comando termina con 0 aunque la revisión falle.
