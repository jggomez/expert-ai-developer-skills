# Guía de pr-reviewer

Instala el revisor en un repositorio y cambia lo que revisa.

## Qué necesitas

- Un repositorio de GitHub donde puedas añadir secretos y workflows.
- Una [clave de API de Gemini](https://aistudio.google.com/apikey) o de
  [Anthropic](https://platform.claude.com/settings/keys). Para probar la instalación no necesitas ninguna.

No se ejecuta nada en tu ordenador ni en un servidor tuyo. Las revisiones corren en los runners de GitHub Actions.

## Instalar con Gemini

1. **Guarda la clave.** En tu repositorio, abre **Settings → Secrets and variables → Actions → Secrets** y añade
   `GEMINI_API_KEY`.
2. **Añade el workflow.** Copia [`examples/pr-review.yml`](../examples/pr-review.yml) a
   `.github/workflows/pr-review.yml`.
3. **Fija la versión.** Obtén un SHA de commit y sustituye `<commit-sha>` por él:

   ```bash
   git ls-remote https://github.com/jggomez/expert-ai-developer-skills refs/heads/main
   ```

4. **Haz merge del workflow a tu rama por defecto.** Los comentarios `/review` solo funcionan desde ahí.
5. **Abre un pull request.** En unos minutos recibe comentarios en línea y un resumen con el modelo, los tokens y
   el coste estimado.

## Instalar con Claude

Claude necesita un paso más, una sola vez, porque Managed Agents guarda el agente en tu cuenta de Anthropic. No
queda nada corriendo en tu ordenador.

1. Crea el agente, desde un clon de este repositorio:

   ```bash
   cd tools/pr-reviewer
   uv sync --extra claude
   export ANTHROPIC_API_KEY=tu_clave
   uv run pr-reviewer setup-claude
   ```

2. Añade el secreto `ANTHROPIC_API_KEY`.
3. Añade tres variables del repositorio: `CLAUDE_AGENT_ID` y `CLAUDE_ENVIRONMENT_ID` con los ID impresos, y
   `PR_REVIEW_PROVIDER` con el valor `claude`.

Borra `PR_REVIEW_PROVIDER` para volver a Gemini.

## Instalar con un plan Claude Pro o Max

Usa tu suscripción en vez de pagar por tokens. Las revisiones usan la
[Action oficial de Claude Code](https://code.claude.com/docs/en/github-actions) y cuentan contra los límites de tu
plan.

1. Crea un token en tu ordenador:

   ```bash
   claude setup-token
   ```

2. Añádelo como el secreto `CLAUDE_CODE_OAUTH_TOKEN`.
3. Añade la variable del repositorio `PR_REVIEW_PROVIDER` con el valor `claude-code`.

El token pertenece a quien lo creó, así que nunca lo compartas. Cada persona o dueño de repositorio usa el suyo.
Para un equipo u organización, usa en `api-key` una clave de la [Claude Console](https://platform.claude.com).

Este proveedor revisa en una sola pasada, sin grupos, lee toda la copia limpia con herramientas de solo lectura y
no muestra coste. El token de GitHub también llega a este paso, porque la Action oficial necesita uno.

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
