# agent-meter: Métricas de Tokens, Costo y Latencia para Agentes de Código con IA

`agent-meter` ofrece visibilidad por proyecto sobre cuánto cuestan y cómo rinden los agentes de código con IA. Cubre **Claude Code** y **Antigravity** (CLI, IDE y aplicación), incluso cuando el mismo proyecto se trabaja alternando entre herramientas de un día para otro. Funciona primero en local, tiene costo **$0** y es completamente **opcional**.

> **Guías de usuario:** la instalación paso a paso y el uso de ambas opciones (modo local y BigQuery + Looker Studio) están en
> [`tools/agent-meter/README.es.md`](../../tools/agent-meter/README.es.md) (español) y
> [`tools/agent-meter/README.md`](../../tools/agent-meter/README.md) (English). Esta página es el resumen de diseño.

Lee los transcripts y bases de datos que las herramientas ya escriben en tiempo real en macOS, Linux y Windows (PowerShell/CMD o WSL2), por lo que no se pierde nada ante cierres inesperados. Es un **recolector incremental e idempotente**: ejecutarlo dos veces nunca duplica conteos. El almacén local es la fuente de verdad y la nube es únicamente una réplica.

| Métrica | Por qué importa |
| :--- | :--- |
| Costo equivalente de API (`≈ USD`) por proyecto, cliente, host, modelo y día | Márgenes, elección de plan, facturación mensual |
| Tokens por tipo (input / output / cache write / cache read) y tasa de acierto de caché | Los verdaderos impulsores del costo; las lecturas de caché dominan el volumen bruto |
| Latencia de tareas P50 / P95 / P99, tiempo activo frente a tiempo reloj | Experiencia normal frente a tareas bloqueadas o en bucle |
| Resumen por tarea: subagentes por tipo, profundidad máxima, paralelismo, ruta crítica, reintentos | Cuánto cuesta una ejecución multiagente y en qué se va el tiempo |
| Costo de IA frente al valor facturable por cliente y mes | "El costo de IA fue el 4% de lo facturado al cliente Z" |
| Conteo de llamadas a herramientas y archivos tocados (solo conteos) | Qué hizo el agente, sin almacenar contenido |

## Opción A frente a Opción B

| | **Opción A: Local** (por defecto, siempre activa) | **Opción B: Nube** (opcional, sobre A) |
| :--- | :--- | :--- |
| Audiencia | Cualquier desarrollador, sin cuenta en la nube | Desarrolladores con un proyecto en GCP |
| Almacenamiento | DuckDB en `~/.agent-meter/meter.duckdb` | A + dataset de BigQuery `agent_metrics` (solo trabajos de carga por lotes) |
| Visualización | Resumen al final de cada tarea o sesión, `agent-meter last` / `tasks`, reporte HTML sin conexión (`agent-meter report --open`) | Tablero en Looker Studio con desglose proyecto → sesión → tarea → ejecución de agente → llamada |
| Red | Ninguna. `setup --local --yes` hace cero llamadas de red | Trabajos de carga en BigQuery. Los periodos sin conexión se encolan en un outbox local |
| Costo | $0 | $0 dentro de la capa gratuita de BigQuery |
| Modos | — | `billing` (facturación vinculada, alerta de presupuesto opcional de $1 que notifica pero **no limita** el gasto) o `sandbox` (sin tarjeta, expiración de tablas a 60 días, recarga completa semanal) |

Looker Studio muestra **los mismos totales** que el reporte local: `agent-meter verify --reconcile --cloud` debe reportar 0 diferencias.

## Canales de Instalación

El CLI es el producto. Ambos plugins son formas opcionales de registrar sus hooks.

| Canal | Para quién | Cómo |
| :--- | :--- | :--- |
| **1. CLI independiente** (principal) | Cualquier usuario, con o sin los plugins de este repositorio | `uv tool install` o `pipx install`, luego `agent-meter setup`. Con consentimiento, registra los hooks en `~/.claude/settings.json` y `~/.gemini/config/hooks.json` (con copia de seguridad y fusión, sin sobrescribir) y/o el programador periódico (`launchd` en macOS, `systemd`/`cron` en Linux, Programador de tareas `schtasks` en Windows) |
| **2. Plugin opcional `agent-metrics`** | Usuarios del marketplace que prefieren plugins | [Plugin de Claude Code](../../plugins/claude/agent-metrics/README.md) o [Plugin de Antigravity](../../plugins/antigravity/agent-metrics/README.md). Incluye los hooks y una skill de configuración. Los hooks no hacen nada (salen con 0 y un aviso en stderr) si el CLI no está instalado |
| **3. Sin hooks** | Usuarios que no desean hooks en sus herramientas | Solo programador periódico (cada 15 min) o `agent-meter collect` manual. Los resúmenes se consultan con `agent-meter last` / `agent-meter tasks --last` |

```bash
# macOS, Linux o Windows (PowerShell/CMD o WSL2, %USERPROFILE%\.local\bin) — Python ≥ 3.11 (uv instala el intérprete automáticamente)
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"
# o con pipx
pipx install --python python3.12 "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

agent-meter setup --local                                         # Opción A
agent-meter setup --cloud --gcp-project <project> --mode billing  # Opción B (requiere el extra [bigquery])
agent-meter doctor
```

Ningún plugin o skill existente en este repositorio depende de `agent-meter`, lo referencia ni cambia su comportamiento por él.

## Hooks y Programador Periódico (Scheduler)

| Host | Evento | Comando | Salida |
| :--- | :--- | :--- | :--- |
| Claude Code | `SessionEnd` | `agent-meter hook --host claude-code --event session-end` | nada en stdout |
| Claude Code | `Stop` (cada tarea) | `agent-meter hook --host claude-code --event task-end` | nada en stdout |
| Antigravity | `Stop` (cada tarea) | `agent-meter hook --host antigravity --event task-end` | exactamente `{}` |

El programador periódico ejecuta `agent-meter collect --scheduled --quiet` cada 15 minutos mediante `launchd` en macOS, `systemd` user timer o `cron` en Linux, y el Programador de tareas de Windows (`schtasks`, tarea `com.agent-meter.collect`) en Windows.

## Documentos

| Documento | Contenido |
| :--- | :--- |
| [PRD.md](PRD.md) | Personas, historias de usuario (US-01..US-17), reglas de negocio, RNF |
| [ADR-001-agent-meter.md](ADR-001-agent-meter.md) | Decisiones de arquitectura: lectores, esquema v1, triggers y hooks (§3.10), sink de BigQuery (§3.11) |
| [contracts.md](contracts.md) | Contratos de interfaz, esquema DuckDB, vistas del almacén, outbox y tablas de BigQuery |
| [looker-studio.md](looker-studio.md) | Construcción del tablero de Looker Studio sobre las vistas de BigQuery |
| [pricing-sources.md](pricing-sources.md) | Origen de cada precio incluido por defecto |
| [spike-notes.md](spike-notes.md) | Datos verificados de cada host: formatos de transcript, eventos de hooks y payloads |
| [build-notes.md](build-notes.md) | Notas de construcción y desviaciones aceptadas |
