# agent-meter — Guía en español

> **¿Cuánto me cuestan mis agentes de IA por proyecto, por tarea y por subagente, y cuánto se demoran?**

`agent-meter` lo responde para **Claude Code** y **Antigravity** (CLI, IDE y la app "Antigravity 2.0"). Lee los archivos
que esas herramientas ya guardan en tu computador y te entrega:

- un **resumen corto al terminar cada tarea o sesión** (tokens, costo equivalente, tiempo, P50/P95),
- un **reporte HTML** que se abre en el navegador y funciona sin internet,
- y, si quieres, un **dataset en BigQuery + tablero en Looker Studio** en tu propio proyecto de Google Cloud.

Es **gratis** (el modo local no necesita ninguna cuenta), **solo lee** los datos de tus herramientas y es **privado**: nunca
guarda prompts, código, entradas o salidas de herramientas ni rutas de archivos.

> English version: [README.md](README.md)

---

## Índice

1. [Dos formas de usarlo](#1-dos-formas-de-usarlo)
2. [Inicio rápido (5 minutos, local)](#2-inicio-rápido-5-minutos-local)
3. [Cómo funciona](#3-cómo-funciona)
4. [Instalación](#4-instalación)
5. [Opción A — Local (DuckDB + reporte HTML)](#5-opción-a--local-duckdb--reporte-html)
6. [Opción B — Nube (BigQuery + Looker Studio)](#6-opción-b--nube-bigquery--looker-studio)
7. [Referencia de comandos](#7-referencia-de-comandos)
8. [Cómo leer los números](#8-cómo-leer-los-números)
9. [Proyectos, clientes, tarifas y horas](#9-proyectos-clientes-tarifas-y-horas)
10. [Precios configurables](#10-precios-configurables)
11. [Referencia de configuración](#11-referencia-de-configuración)
12. [Hooks, timer y notificaciones](#12-hooks-timer-y-notificaciones)
13. [Privacidad y archivos](#13-privacidad-y-archivos)
14. [Herramientas soportadas](#14-herramientas-soportadas)
15. [Problemas comunes](#15-problemas-comunes)
16. [Desinstalar](#16-desinstalar)

---

## 1. Dos formas de usarlo

| | **Opción A — Local** (por defecto) | **Opción B — Nube** (opcional, encima de A) |
| :--- | :--- | :--- |
| Para quién | Cualquier desarrollador, sin cuenta en la nube | Quien tenga un proyecto de Google Cloud |
| Dónde quedan los datos | `~/.agent-meter/meter.duckdb` en tu Mac/Linux | El mismo archivo local **más** un dataset en BigQuery |
| Dónde los ves | Resúmenes en la terminal + `agent-meter report` (HTML) | Todo lo de A **más** un tablero en Looker Studio |
| Internet | Nunca | Solo para subir a BigQuery (cargas por lote) |
| Costo | $0 | $0 dentro del nivel gratuito de BigQuery para este volumen (las cargas por lote son gratis); pon una alerta de presupuesto |

La opción B es una **copia** de la A: lo local siempre es la fuente de verdad y la nube se puede reconstruir en cualquier
momento (`agent-meter sync --full-reload`).

---

## 2. Inicio rápido (5 minutos, local)

```bash
# 1) Instalar (necesitas uv: https://docs.astral.sh/uv/)
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# 2) Configurar una sola vez: detecta Claude Code / Antigravity e importa tu historial
agent-meter setup --local

# 3) Usarlo
agent-meter last            # resumen de tu última sesión
agent-meter tasks --last 5  # las últimas 5 tareas, con cada subagente
agent-meter report --open   # reporte completo en el navegador
```

Listo. Si en el `setup` elegiste hooks o el timer, lo nuevo se registra solo; si no, corre `agent-meter collect` cuando
quieras números frescos.

> ¿Vas a instalar desde una rama que aún no está en `main`, o desde una copia local del repo? Mira la [§4](#4-instalación).

---

## 3. Cómo funciona

```
 Transcripts de Claude Code (~/.claude/projects)       Bases de Antigravity (~/.gemini/antigravity-*/)
                 │                                                        │
                 └──────────────────┬─────────────────────────────────────┘
                                    ▼
                 agent-meter collect   (incremental, sin duplicar, solo lectura)
                                    │   lo disparan: hooks (al terminar tarea/sesión), el timer (cada 15 min) o tú
                                    ▼
                 ~/.agent-meter/meter.duckdb   ← fuente de verdad (tokens, tiempos, proyectos, tareas, agentes)
                    │                    │                                  │
         agent-meter last / tasks   agent-meter report (HTML)     agent-meter sync  ──►  BigQuery  ──►  Looker Studio
              (terminal)              (sin internet)                 (solo opción B)
```

- **No se pierde nada** si una sesión se cae o nunca la cierras: las herramientas siguen escribiendo sus archivos y el
  siguiente `collect` retoma donde quedó.
- **No se cuenta doble**: cada llamada tiene una llave única; correr `collect` varias veces siempre es seguro.
- **El costo se calcula al consultar**, con tokens × tabla de precios. Si corriges o agregas un precio, todo tu historial
  se recalcula al instante (en BigQuery después del siguiente `sync`).

---

## 4. Instalación

**Requisitos:** macOS o Linux, Python ≥ 3.11 (`uv` lo instala por ti) y `uv` o `pipx`.

### 4.1 Desde GitHub (recomendado)

```bash
# Solo modo local
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# Local + soporte para BigQuery (opción B)
uv tool install "agent-meter[bigquery] @ git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# Lo mismo con pipx
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
```

Para instalar desde una rama específica (por ejemplo, antes de unirla a `main`), agrega `@<rama>` justo después de la URL
del repositorio:

```bash
uv tool install "agent-meter[bigquery] @ git+https://github.com/jggomez/expert-ai-developer-skills@feature/agent-metrics#subdirectory=tools/agent-meter"
```

### 4.2 Desde una copia local del repositorio

```bash
cd /ruta/a/expert-ai-developer-skills
uv tool install "./tools/agent-meter"               # modo local
uv tool install "./tools/agent-meter[bigquery]"     # con soporte para BigQuery
```

### 4.3 Verificar, actualizar o quitar el programa

```bash
agent-meter --version            # ej. agent-meter 0.1.0
uv tool upgrade agent-meter      # actualizar (o: uv tool install --force <mismo origen>)
uv tool uninstall agent-meter    # quitar el programa (antes corre `agent-meter uninstall`, ver §16)
```

### 4.4 Opcional: el plugin `agent-metrics`

Si ya usas el marketplace de plugins de este repositorio, puedes registrar los hooks con el plugin opcional en vez de con
`setup`. **El CLI sigue siendo necesario** (el plugin solo lo llama).

```text
/plugin marketplace add jggomez/expert-ai-developer-skills
/plugin install agent-metrics@expert-ai-developer-skills
```

Ningún otro plugin del repositorio depende de agent-meter; instalarlo o quitarlo no cambia nada más.

---

## 5. Opción A — Local (DuckDB + reporte HTML)

### 5.1 Correr el asistente de configuración

```bash
agent-meter setup --local
```

Son 8 pasos. Todos se pueden repetir sin problema: si corres `setup` dos veces, la segunda no cambia nada.

| Paso | Qué pregunta / hace | Respuesta recomendada |
| :--- | :--- | :--- |
| 1. Herramientas | Detecta Claude Code (`~/.claude`) y Antigravity CLI/IDE/app (`~/.gemini/...`) y cuánto historial hay | Deja todas las detectadas |
| 2. Modo | Local o Local + Nube | Local (la nube la agregas después) |
| 3. Disparadores | Cómo se registra lo nuevo: **hooks**, **timer**, ambos o ninguno (ver abajo) | `hooks,scheduler` |
| 4. Privacidad | Anonimizar nombres de proyecto al subir a la nube (solo aplica a la opción B) | No, si el proyecto es tuyo |
| 5. Historial | Importar tu historial ahora | Sí |
| 6. Proyectos | Opcional: nombres, clientes y tarifas (se puede hacer después, §9) | Saltar por ahora |
| 7. Nube | Solo en modo nube (§6) | — |
| 8. Resumen | Muestra lo que cambió y corre `doctor` | — |

**Disparadores — qué cambia en tu máquina cada uno:**

| Disparador | Qué hace | Qué modifica |
| :--- | :--- | :--- |
| `hooks` | Resumen apenas termina cada tarea (Claude Code `Stop`/`SessionEnd`, Antigravity `Stop`) | Agrega entradas a `~/.claude/settings.json` y `~/.gemini/config/hooks.json`: primero te muestra el JSON exacto, hace respaldo y **nunca toca tus hooks existentes** |
| `scheduler` (timer) | Recoge cada 15 minutos, incluidas sesiones caídas o abiertas; en la opción B también sube a BigQuery | Agrega un agente de usuario de `launchd` (macOS) o un timer de systemd / cron (Linux) |
| `none` | Nada automático; tú corres `agent-meter collect` | Nada |

Variantes sin preguntas:

```bash
agent-meter setup --local --yes                               # acepta lo recomendado, cero llamadas de red
agent-meter setup --local --yes --triggers none               # solo importa el historial, no cambia nada más
agent-meter setup --local --yes --triggers scheduler          # solo el timer de 15 minutos
agent-meter setup --local --yes --hosts claude-code           # solo Claude Code
agent-meter setup --local --yes --no-backfill                 # sin importar el historial
```

### 5.2 Uso diario

```bash
agent-meter last                       # resumen de la última sesión (+ hoy / mes de ese proyecto)
agent-meter last --project webpage-devhack
agent-meter tasks --last 10            # últimas 10 tareas con desglose por agente
agent-meter tasks --since 2026-10-01 --project webpage-devhack
agent-meter collect                    # actualizar ya (incremental)
agent-meter projects list              # todos los proyectos con sesiones y costo
```

Ejemplo de resumen de sesión:

```
[agent-meter] expert-ai-developer-skills · Claude Code · session 20h 55m (active 2h 47m)
  Tokens 1.7K in · 138.79M cache read · 6.56M cache write · 639K out · cache hit 95%
  Cost ≈ $77.54 · 45 tasks · P50 50s · P95 2h 32m
  expert-ai-developer-skills today ≈ $33.10 (Claude Code $33.10) · month ≥ $89.53
```

Ejemplo de tarea con subagentes:

```
[agent-meter] proyecto-x · Claude Code · task #12 · 13m 02s (active 11m 40s)
  Cost ≈ $4.10 · 6 agents (max depth 1) · parallelism 2.7x · 1 retry
  main                 $0.40    9 calls
  code-implementer ×2  $2.90  188 calls · 41 Edit · 12 Write
  qa-tester            $0.50   22 calls
  compliance-verifier  $0.30   14 calls
```

### 5.3 El reporte HTML

```bash
agent-meter report --open                                   # todo el historial, abre el navegador
agent-meter report --open --month 2026-10                   # un mes
agent-meter report --open --from 2026-10-01 --to 2026-10-15 # un rango de fechas
agent-meter report --open --project webpage-devhack         # un proyecto
agent-meter report --open --client "Cliente A"              # todos los proyectos de un cliente
agent-meter report --out ~/Desktop/costos-ia-oct.html       # guardar en un archivo específico
```

Es un solo archivo, funciona sin internet. Tema claro por defecto; el modo oscuro sigue a tu sistema. Secciones: resumen
(costo por proyecto/mes, Claude Code contra Antigravity), tareas y agentes, rendimiento (P50/P95/P99), eficiencia (caché,
tamaño del contexto), facturación (si hay tarifas) y avisos (sin precio, estimados, historial no medido). Cada gráfica
tiene un botón **Table view** para ver los datos en tabla.

---

## 6. Opción B — Nube (BigQuery + Looker Studio)

### 6.1 Requisitos (una sola vez)

| # | Qué | Cómo |
| :--- | :--- | :--- |
| 1 | CLI `gcloud` | https://cloud.google.com/sdk/docs/install |
| 2 | agent-meter con soporte BigQuery | Instalar con el extra `[bigquery]` (§4) |
| 3 | Iniciar sesión para aplicaciones (ADC) | `gcloud auth application-default login` |
| 4 | (Recomendado) proyecto de cuota para ADC | `gcloud auth application-default set-quota-project <PROJECT_ID>` |
| 5 | Un proyecto de GCP | Uno que ya tengas (idealmente de desarrollo, no de producción) |
| 6 | Modo | **billing** (recomendado): facturación activa, queda dentro del nivel gratuito para este volumen · **sandbox**: sin tarjeta, pero BigQuery borra las tablas a los 60 días (agent-meter vuelve a subir todo cada semana) |
| 7 | Permisos | **Owner** del proyecto, o `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` |

No tienes que activar APIs a mano: el asistente revisa cada requisito y te muestra el comando exacto para arreglar lo que
falte (`gcloud services enable bigquery.googleapis.com --project …`, permisos, etc.).

> agent-meter **siempre usa el proyecto que le indicas**, nunca el proyecto por defecto de tu `gcloud`.

### 6.2 Conectar

```bash
agent-meter setup --cloud --gcp-project <PROJECT_ID> --mode billing
# sin preguntas y sin tocar hooks ni el timer:
agent-meter setup --cloud --gcp-project <PROJECT_ID> --mode billing --triggers none --yes
```

Qué pasa:

1. Revisa requisitos: `gcloud`, ADC, proyecto, facturación, API de BigQuery y permisos (`agent-meter doctor --cloud` hace
   la misma revisión).
2. **Alerta de presupuesto (modo billing)**: ofrece crear una **alerta de $1** en la cuenta de facturación del proyecto
   (activa por ti la API de Budgets). La alerta solo te avisa por correo al 50% y al 100%; **no** pone tope al gasto.
3. Crea el dataset `agent_metrics` (ubicación `US` por defecto) con sus tablas y vistas.
4. Sube todo tu historial y comprueba que los totales en BigQuery sean iguales a los locales.

### 6.3 Qué se crea en BigQuery

| Tipo | Nombres |
| :--- | :--- |
| Tablas de hechos (particiones mensuales) | `raw_llm_calls`, `raw_tasks`, `raw_agent_runs`, `raw_sessions`, `raw_tool_uses` |
| Tablas de referencia | `projects`, `pricing`, `pricing_aliases`, `host_defaults`, `dev_hours_manual`, `dev_hours_derived`, `task_tags`, `tag_history`, `settings`, `untracked` |
| Vistas sin duplicados | `llm_calls`, `tasks`, `agent_runs`, `sessions`, `tool_uses` |
| **Vistas para tableros** | `v_daily_project_cost`, `v_calls`, `v_sessions`, `v_tasks`, `v_agent_runs`, `v_agent_type_cost`, `v_task_latency`, `v_tool_counts`, `v_client_month`, `v_dev_hours`, `v_unpriced_models`, `v_untracked`, `v_health` |

Solo se suben números y metadatos (tokens, tiempos, modelos, nombres de proyecto/cliente, tipos de agente, nombres y
conteos de herramientas). Con `agent-meter config set bigquery.anonymize_projects true` los nombres de proyecto, cliente,
remoto y etiquetas se suben como hash con sal (la sal nunca sale de tu máquina).

### 6.4 Mantenerlo actualizado

```bash
agent-meter sync                 # sube lo que cambió desde el último sync (solo cargas por lote)
agent-meter sync --dry-run       # muestra qué se subiría
agent-meter sync --full-reload   # reconstruye todas las tablas desde lo local (sandbox lo hace cada semana)
agent-meter verify --reconcile --cloud --from 2026-10-01 --to 2026-10-31   # local contra BigQuery; sale con 5 si hay diferencias
```

Con el timer (`scheduler`), cada corrida de 15 minutos también sincroniza. Sin el timer, corre
`agent-meter collect && agent-meter sync`.

Consulta rápida desde la terminal:

```bash
bq query --project_id=<PROJECT_ID> --use_legacy_sql=false \
  'SELECT display_name, ROUND(SUM(cost_usd),2) AS cost_usd, SUM(calls) AS calls
   FROM `<PROJECT_ID>.agent_metrics.v_daily_project_cost` GROUP BY 1 ORDER BY 2 DESC LIMIT 10'
```

### 6.5 Armar el tablero en Looker Studio

Looker Studio (https://lookerstudio.google.com) es la herramienta **gratuita** de tableros web de Google; entras con tu
cuenta de Google. (No es "Looker", el producto empresarial de pago.)

1. **Crear → Informe → Agregar datos → BigQuery**.
2. Elige **tu proyecto → `agent_metrics` → `v_daily_project_cost`** (puedes escribir el id en *Enter project ID manually*) → **Agregar**.
3. Looker Studio avisa que la fuente usa las **credenciales del propietario**: si compartes el informe, quien lo vea podrá
   ver los datos. No hay problema mientras sea solo tuyo. Acepta.
4. Agrega las gráficas. Este diseño da un tablero claro y formal:

| Gráfica | Tipo | Dimensión | Métrica | Consejo |
| :--- | :--- | :--- | :--- | :--- |
| Costo total | Scorecard | — | `cost_usd` (suma, tipo *Moneda USD*) | Duplícala para `calls`, `output_tokens`, `cache_read_tokens` (activa *Compact numbers*) |
| Costo diario | Serie temporal | `local_date` | `cost_usd` | Oculta la leyenda |
| Costo por proyecto | Tabla con mapa de calor | `display_name` | `calls`, `cost_usd` | Ordena por `cost_usd` descendente |
| Costo por herramienta | Dona | `host` | `cost_usd` | Leyenda a la derecha |
| Costo mensual | Columnas | `local_month` | `cost_usd` | Ordena por `local_month` ascendente y muestra etiquetas de datos |
| Filtro de periodo | Control de rango de fechas | — | — | Usa `local_date` |

5. Estilo del tablero de referencia: fondo de página `#EEF2F7`, tarjetas blancas (radio 12, borde claro, sombra), banda de
   encabezado con degradado índigo→violeta (`#312E81` → `#7C3AED`) y título en blanco, letra Roboto, y paleta de gráficas
   `#4F46E5` (índigo), `#14B8A6` (verde azulado), `#F59E0B` (ámbar), `#EC4899` (rosa). En **Tema y diseño → Personalizar**
   cambias de una vez el fondo, la letra, el fondo de los componentes y la paleta de todas las gráficas.
6. Para más detalle (sesiones, tareas, agentes, latencia, caché), agrega fuentes de datos para `v_sessions`, `v_tasks`,
   `v_agent_runs`, `v_agent_type_cost` y `v_task_latency`. Detalle por página:
   [`docs/agent-metrics/looker-studio.md`](../../docs/agent-metrics/looker-studio.md).

> Si haces clic en una fila o en una porción de la dona, se aplica un **filtro cruzado** a toda la página. Quítalo con
> **Reset** (arriba).

> Looker Studio guarda en caché los resultados: los datos nuevos aparecen después del siguiente `agent-meter sync` y de que
> venza la caché (o con *Actualizar datos* en el menú del informe).

---

## 7. Referencia de comandos

Opciones globales (antes del comando): `--home <carpeta>` (o `$AGENT_METER_HOME`; por defecto `~/.agent-meter`) y
`--quiet`. La mayoría de comandos de lectura aceptan `--json`.

| Comando | Para qué | Opciones más útiles |
| :--- | :--- | :--- |
| `setup` | Configuración guiada (local o nube) | `--local`/`--cloud`, `--yes`, `--hosts`, `--triggers hooks,scheduler\|hooks\|scheduler\|none`, `--gcp-project`, `--mode billing\|sandbox`, `--no-backfill` |
| `collect` | Importación incremental | `--host H`, `--since AAAA-MM-DD`, `--full` (relee todo, sin duplicar) |
| `last` | Resumen de la última sesión | `--project P`, `--json` |
| `tasks` | Tareas con sus subagentes | `--last [N]`, `--session S`, `--project P`, `--tag T`, `--since D`, `--json` |
| `report` | Reporte HTML | `--open`, `--out F`, `--month AAAA-MM`, `--from D --to D`, `--project P`, `--client C` |
| `projects list` | Proyectos con sesiones y costo | `--json` |
| `projects set <proyecto>` | Nombre, cliente y cobro | `--name`, `--client`, `--billing hourly\|fixed`, `--rate`, `--price`, `--currency` |
| `projects merge <origen> <destino>` | Unir dos ids de proyecto en uno | — |
| `hours set <proyecto> <AAAA-MM-DD\|AAAA-MM> <horas>` · `hours unset` · `hours list` | Horas de trabajo manuales (reemplazan el cálculo automático) | — |
| `tag "<nombre>"` | Agrupar tareas en un trabajo (ej. un ticket) | `--last N`, `--project P`, `--clear` |
| `pricing list\|unpriced\|add\|set\|alias\|remove\|validate` | Tabla de precios (§10) | ver §10 |
| `config show\|get\|set\|edit` | Configuración (§11) | `config set <clave> <valor>` |
| `doctor` | Revisión de salud (hooks, timer, formatos, precios, historial no medido) | `--cloud`, `--json` |
| `verify --reconcile` | Local contra una relectura independiente (o contra BigQuery con `--cloud`) | `--from`, `--to`, `--host`, `--cloud` |
| `sync` | Subir a BigQuery | `--full-reload`, `--dry-run` |
| `uninstall` | Quitar hooks/timer y restaurar tus settings | `--keep-scheduler`, `--purge --yes` |

Códigos de salida: `0` bien · `1` error · `2` uso incorrecto · `3` `doctor` encontró un FAIL · `4` almacén ocupado
(reintenta) · `5` el cuadre encontró diferencias. El comando interno `hook` siempre sale con `0`.

---

## 8. Cómo leer los números

| Ves | Significa |
| :--- | :--- |
| `≈ $77.54` | **Costo equivalente de API**: lo que costarían esos tokens a precio público de la API. Si pagas suscripción (Claude Max, plan de Google), es el *valor* que consumiste, no lo que te cobraron |
| `≥ $89.53` | Es un **mínimo**: algunas llamadas de ese total no tienen precio o les faltan datos de tokens |
| `*` | El precio es **estimado** (por ejemplo, un modelo interno de Antigravity cobrado como su modelo público más cercano) |
| `†` | El **modelo se dedujo** (la herramienta no lo guardó; se usó `hosts.<herramienta>.default_model`) |
| Tokens *in / cache read / cache write / out* | Entrada nueva / entrada leída de la caché (barata) / entrada escrita en la caché / salida generada (incluye razonamiento) |
| *cache hit* | `cache read ÷ (in + cache read + cache write)`: mientras más alto, más barato |
| *session 20h 55m (active 2h 47m)* | Tiempo de reloj del primer al último evento contra el tiempo en que los agentes realmente trabajaron (pausas mayores a `idle_threshold_s` cuentan como inactivas) |
| *task* (tarea) | Un prompt que enviaste, con todos los subagentes que lanzó |
| *P50 / P95* | Duración mediana y percentil 95 de las tareas |
| *parallelism 2.7x* | Tiempo activo sumado de los agentes ÷ tiempo activo de la tarea (cuánto trabajaron en paralelo) |
| *retry* | El mismo tipo de agente corrió otra vez en la misma tarea (ej. implementador después de una QA fallida) |

---

## 9. Proyectos, clientes, tarifas y horas

Un **proyecto** se identifica por su repositorio git (URL del remoto o raíz), así que el mismo repo abierto desde Claude
Code y desde Antigravity cuenta como **uno solo**. Las carpetas que moviste se unen solas; si aún quedan dos ids para el
mismo proyecto, únelos con `projects merge`.

```bash
agent-meter projects list
agent-meter projects set webpage-devhack --name "Sitio DevHack" --client "DevHack" --billing hourly --rate 45 --currency USD
agent-meter projects set app-cliente --client "Cliente A" --billing fixed --price 3000 --currency USD
agent-meter projects merge path:0a4e234a3424dac3 git:1d58476545c17b30
```

Las horas de trabajo se estiman con tus sesiones (no se cuentan las pausas mayores a `dev_hours_merge_gap_min` entre
tareas). Si sabes el número real, ponlo:

```bash
agent-meter hours set webpage-devhack 2026-10 32       # 32 horas en octubre
agent-meter hours set webpage-devhack 2026-10-18 4     # 4 horas en un día
agent-meter hours list
agent-meter hours unset webpage-devhack 2026-10
```

Con tarifas, el reporte y la vista `v_client_month` muestran **costo de IA contra valor facturable** por cliente y mes.

Agrupar varios prompts en un **trabajo** (ej. un ticket):

```bash
agent-meter tag "TICKET-123"            # etiqueta las tareas actuales/siguientes
agent-meter tag "TICKET-123" --last 5   # etiqueta las 5 tareas más recientes
agent-meter tag --clear
agent-meter tasks --tag "TICKET-123"
```

Para ver montos en tu moneda junto al USD: `agent-meter config set currency.display COP` y
`agent-meter config set currency.usd_rate 4100` (unidades de esa moneda por 1 USD).

---

## 10. Precios configurables

Ningún precio está fijo en el código. Se combinan dos niveles y **tu archivo local siempre gana**:

| Archivo | Quién lo mantiene | Contenido |
| :--- | :--- | :--- |
| `pricing.yaml` (viene con agent-meter) | Cada versión de agent-meter | Precios oficiales de Anthropic y Google con URL de la fuente y ventanas de fechas; alias para los modelos internos de Antigravity (marcados como *estimados*) |
| `~/.agent-meter/pricing.local.yaml` | Tú | Modelos nuevos, correcciones, tus propios alias |

Cada modelo puede tener varias **ventanas de precio** (`effective_from`), así que un cambio de precio nunca altera tus
meses pasados.

```bash
agent-meter pricing list                       # todos los modelos, ventanas y fuentes
agent-meter pricing unpriced                   # modelos en tus datos sin precio (+ el comando exacto para arreglarlo)

# Agregar un modelo nuevo (USD por millón de tokens)
agent-meter pricing add gemini-5-flash --input 1.00 --output 5.00 --cache-read 0.10 --effective-from 2026-11-01 \
  --source-url https://ai.google.dev/gemini-api/docs/pricing

# Un cambio de precio desde una fecha (los tres precios principales son obligatorios)
agent-meter pricing set claude-sonnet-5 --input 2.00 --output 12.00 --cache-read 0.20 \
  --cache-write-5m 2.50 --cache-write-1h 4.00 --effective-from 2026-12-01

# Asignar un id desconocido o interno a un modelo con precio
agent-meter pricing alias agy-demo-high gemini-3.8-flash --estimated

agent-meter pricing remove --alias agy-demo-high
agent-meter pricing remove --model gemini-5-flash --effective-from 2026-11-01
agent-meter pricing validate                   # revisa pricing.local.yaml
```

Reglas:

- Un modelo sin precio igual se registra (se guardan los tokens) y se muestra como `≥ $X (N calls unpriced)`, **nunca $0**.
- Los precios se aplican al consultar, así que `pricing add/set/alias` recalcula el historial al momento (BigQuery después del siguiente `sync`).
- Para precios por tramos (más caro por encima de cierto tamaño de prompt) usa `--min-prompt-tokens`.
- Si `pricing.local.yaml` es inválido, se sigue usando la última tabla válida y `doctor` lo reporta.
- Antigravity a veces no guarda el modelo; esas llamadas se cobran como `hosts.<herramienta>.default_model` (por defecto
  `gemini-3.8-flash`) y se marcan con `†`.

---

## 11. Referencia de configuración

`agent-meter config show` muestra todo; cambia valores con `agent-meter config set <clave> <valor>`. El archivo es
`~/.agent-meter/config.toml`.

| Clave | Por defecto | Significado |
| :--- | :--- | :--- |
| `timezone` | la zona de tu sistema | Límites de día y mes (ej. `America/Bogota`) |
| `idle_threshold_s` | `120` | Pausas dentro de una tarea mayores a esto cuentan como inactivas |
| `stale_after_h` | `24` | Una tarea sin evento de fin se cierra tras estas horas sin actividad |
| `dev_hours_merge_gap_min` | `30` | Pausas entre tareas mayores a esto no cuentan como horas de trabajo |
| `show_task_labels` | `true` | Muestra un extracto corto del prompt en `tasks` (solo en la terminal, nunca se guarda) |
| `notify` | `auto` | Notificaciones: `auto` (fin de sesión + tareas largas), `session`, `long-tasks`, `off` |
| `notify_min_task_s` | `120` | Duración mínima para avisar de una "tarea larga" |
| `claude_inline_summary` | `false` | Reservado (los resúmenes dentro del chat de Claude Code están apagados) |
| `store_agent_descriptions` | `false` | Reservado para v2, hoy se ignora (las descripciones siempre se guardan como hash) |
| `currency.display`, `currency.usd_rate` | — | Mostrar una segunda moneda, ej. `COP` y `4100` (unidades por 1 USD) |
| `hosts.<herramienta>.enabled` | `true` | Recoger de `claude-code`, `antigravity-cli`, `antigravity-ide`, `antigravity-app` |
| `hosts.<herramienta>.root` | (automático) | Carpeta de datos personalizada para esa herramienta |
| `hosts.<herramienta>.default_model` | `gemini-3.8-flash` en Antigravity | Modelo que se asume cuando la herramienta no lo guarda |
| `bigquery.enabled` | `false` | Lo activa `setup --cloud` |
| `bigquery.project`, `bigquery.dataset`, `bigquery.location` | —, `agent_metrics`, `US` | A dónde se sube |
| `bigquery.mode` | `billing` | `billing` o `sandbox` |
| `bigquery.anonymize_projects` | `false` | Subir nombres de proyecto/cliente/remoto/etiqueta como hash con sal |
| `bigquery.looker_template_id` | — | Id opcional de un informe plantilla para copiarlo con un clic (no es necesario) |

---

## 12. Hooks, timer y notificaciones

**Hooks** (los agrega `setup` con el disparador `hooks`, o el plugin opcional):

| Herramienta | Archivo | Evento |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/settings.json` | `Stop` (fin de cada tarea) y `SessionEnd` |
| Antigravity (CLI, IDE, app) | `~/.gemini/config/hooks.json` (hook con nombre `agent-meter`) | `Stop` (fin de cada tarea) |

El hook responde en menos de ~2 segundos, nunca bloquea a tu agente, **no agrega nada** al contexto del agente (cero
tokens), siempre sale con 0 y hace la importación en un proceso aparte en segundo plano. `~/.gemini/settings.json` (de
Gemini CLI) nunca se modifica.

**Timer:** cada 15 minutos (agente de usuario de `launchd` con `RunAtLoad` en macOS; timer de usuario de systemd con
`Persistent=true` o cron en Linux). Recoge sesiones que se cayeron o nunca se cerraron y, en la opción B, sincroniza con
BigQuery.

**Notificaciones**, solo cuando sirven:

```bash
agent-meter config set notify off               # nunca
agent-meter config set notify session           # solo al terminar una sesión
agent-meter config set notify long-tasks        # solo tareas más largas que notify_min_task_s
agent-meter config set notify_min_task_s 600    # "larga" = 10 minutos
```

El resumen siempre queda guardado en `~/.agent-meter/last-summary.txt` (`agent-meter last` lo muestra).

---

## 13. Privacidad y archivos

**Nunca se guarda ni se sube:** prompts, mensajes del asistente, código, entradas o salidas de herramientas, rutas de
archivos, descripciones de subagentes en texto claro (solo hash con sal), `cli.log`. Los transcripts y las bases de las
herramientas se abren **solo para lectura**.

**Sí se guarda:** cantidades de tokens, fechas, duraciones, modelos, nombres de proyecto/cliente (de git), tipos de agente,
nombres y conteos de herramientas, y errores (solo el tipo).

`~/.agent-meter/` (permisos 0700):

| Archivo | Contenido |
| :--- | :--- |
| `meter.duckdb` | El almacén local |
| `config.toml` | Configuración |
| `projects.yaml` | Proyectos y clientes |
| `pricing.local.yaml` | Tus precios y alias |
| `secret` | Sal local para los hash (nunca se sube) |
| `last-summary.txt` | Último resumen |
| `report.html` | Último reporte (ubicación por defecto) |
| `state/`, `outbox/`, `logs/`, `lock` | Estado interno, preparación de subidas a BigQuery, tipos de error, bloqueo de concurrencia |
| `install.json`, `backups/` | Lo que cambió `setup`, para deshacerlo con `uninstall` |
| `.agent-meter-home` | Marca de que agent-meter creó esta carpeta |

---

## 14. Herramientas soportadas

| Herramienta | De dónde lee | Notas |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/projects/**/*.jsonl` (+ `subagents/`) | Tokens, modelo, tareas y subagentes anidados; las respuestas partidas en varias líneas se deduplican por id de request |
| Antigravity CLI | `~/.gemini/antigravity-cli/conversations/*.db` (+ transcripts, `conversation_summaries.db`) | Tokens, modelo y latencia por llamada; los subagentes son conversaciones hijas |
| Antigravity IDE | `~/.gemini/antigravity-ide/` | Mismo formato que el CLI; no tiene hook al cerrar sesión, así que depende del hook `Stop` o del timer |
| App Antigravity 2.0 | `~/.gemini/antigravity/` | Las conversaciones antiguas guardadas como `.pb` cifrados no se pueden leer; `doctor` las lista como *historial no medido* |

---

## 15. Problemas comunes

**Empieza siempre con `agent-meter doctor`** (agrega `--cloud` para la opción B). Revisa hooks, timer, formatos, precios,
sal, almacén e historial no medido, y te da el arreglo de cada problema.

| Problema | Solución |
| :--- | :--- |
| `agent-meter: command not found` | Revisa que `~/.local/bin` esté en tu `PATH` (`uv tool update-shell`) o reinstala (§4) |
| No hay datos o están viejos | `agent-meter collect` (o revisa hooks/timer con `doctor`) |
| Un costo sale `≥ $0.00` | Ese modelo no tiene precio: `agent-meter pricing unpriced` te da el comando `pricing add`/`alias` exacto |
| El mismo proyecto sale dos veces | `agent-meter projects merge <origen> <destino>` |
| `store busy` (sale con 4) | Hay otra importación corriendo (hook o timer); reintenta en unos segundos |
| Demasiadas notificaciones | `agent-meter config set notify session` u `off` (§12) |
| Nube: credenciales vencidas | `gcloud auth application-default login`; mientras tanto lo local sigue funcionando y el siguiente `sync` sube lo pendiente |
| Nube: aviso "without a quota project" | `gcloud auth application-default set-quota-project <PROJECT_ID>` (si no, es inofensivo) |
| Nube: faltan permisos | Owner, o `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` en el proyecto |
| Nube: no se creó la alerta de presupuesto | La cuenta necesita permisos en la cuenta de facturación; la alerta es opcional |
| Looker muestra números viejos | Corre `agent-meter sync` y luego *Actualizar datos* en el informe |
| En Looker la tabla o la dona filtran todo | Hiciste clic en una fila o porción (filtro cruzado): pulsa **Reset** |
| Los totales no cuadran | `agent-meter verify --reconcile` (y `--cloud` para BigQuery) |

---

## 16. Desinstalar

```bash
agent-meter uninstall                    # quita hooks + timer y restaura tus settings; conserva tus datos
agent-meter uninstall --keep-scheduler   # quita solo los hooks
agent-meter uninstall --purge --yes      # además borra ~/.agent-meter (solo los archivos de agent-meter)
uv tool uninstall agent-meter            # por último, quita el programa
```

`uninstall` restaura un archivo de settings idéntico solo si no lo editaste después del `setup`; si lo editaste, quita
únicamente las entradas de agent-meter. `--purge` se niega a borrar `/`, tu carpeta personal, carpetas con archivos que
agent-meter no creó o carpetas sin su marca.

El dataset de BigQuery **no** se borra solo. Si quieres eliminarlo:
`bq rm -r -d <PROJECT_ID>:agent_metrics`.

---

Documentos de diseño (en inglés): [`docs/agent-metrics/`](../../docs/agent-metrics/) — PRD, ADR-001, contratos, fuentes de
precios, guía de Looker Studio y reporte de cumplimiento.
