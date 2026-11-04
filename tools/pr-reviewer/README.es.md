# pr-reviewer

Una GitHub Action que comenta en los pull requests dónde el código puede ser más eficiente, más simple y
más barato de operar. Solo comenta y nunca bloquea el merge.

[Read in English](README.md)

## Qué revisa

| Eje | Ejemplos |
| --- | --- |
| Eficiencia | Consultas N+1, I/O en bucles, complejidad evitable, memoria sin límite, bloqueos en código async |
| Óptimo | Lógica duplicada, abstracciones innecesarias, estructuras de datos que no encajan con el uso |
| Coste | APIs de pago en bucles, `SELECT *` en almacenes de datos facturados, reintentos sin tope, prompts de LLM enormes, logs excesivos |

Quedan fuera el estilo, los nombres, los tests y la seguridad. Cada hallazgo necesita una línea del diff, un
impacto y un nivel de confianza. Un PR limpio recibe solo un resumen breve de "sin problemas".

## Instalación

1. Crea una [clave de la API de Gemini](https://aistudio.google.com/apikey) en un proyecto con facturación y
   guárdala como el secreto `GEMINI_API_KEY` del repositorio.
2. Copia [`examples/pr-review.yml`](examples/pr-review.yml) en `.github/workflows/pr-review.yml`.
3. Sustituye `<commit-sha>` por el SHA completo de un commit de este repositorio y abre un PR.

Para repetir la revisión, un propietario, miembro o colaborador comenta `/review` en el PR.

> [!WARNING]
> Con la capa gratuita de Gemini, Google puede usar tu código para mejorar sus productos, y revisores humanos
> pueden leerlo. Para código privado usa una clave de pago o Vertex AI. Consulta los
> [términos de la API de Gemini](https://aistudio.google.com/docs/terms).

## Entradas

| Entrada | Por defecto | Descripción |
| --- | --- | --- |
| `api-key` | | Clave de la API de Gemini |
| `provider` | `antigravity` | `antigravity`, o `fake` para probar la instalación sin IA ni clave |
| `model` | `gemini-3.8-flash` | Modelo que se usa |
| `max-tokens` | `200000` | Tope de tokens por revisión |
| `max-findings` | `10` | Máximo de hallazgos publicados |
| `min-severity` | `low` | Severidad mínima que se publica: `critical`, `high`, `medium` o `low` |
| `exclude` | | Patrones de rutas que se omiten, separados por comas o saltos de línea |
| `github-token` | `github.token` | Token para leer el PR y publicar comentarios. Mantén el valor por defecto: las repeticiones reconocen comentarios anteriores por su autor bot |

Por defecto se omiten lockfiles, código generado, artefactos de compilación y dependencias incluidas en el
repo. En diffs grandes se priorizan los archivos fuente, y el resumen lista todo lo que no se revisó.

## Coste

Cada revisión está limitada por `max-tokens`, y el resumen informa los tokens y el coste estimado. Como guía
aproximada y sin medir, una revisión de 40k tokens de entrada y 4k de salida cuesta unos $0.05 con
`gemini-3.8-flash`. Se ejecuta al abrir un PR o marcarlo como listo, y con `/review`, no en cada push.

## Limitaciones

- Se omiten los PR de forks y de Dependabot, porque sus ejecuciones no tienen acceso a secretos.
- Si falla la IA, el resumen lo indica y el job queda en verde.
- El SDK está en la versión 0.1.x, así que la versión va fijada y puede necesitar actualizaciones.

## Seguridad

Quien abre un PR controla el texto que lee el agente, por lo que ese texto se trata como hostil.

- El agente solo tiene herramientas de lectura: sin shell, red, escritura ni subagentes.
- Lee una copia limpia del repositorio, sin `AGENTS.md`, `GEMINI.md`, `.agents/`, `.git` ni symlinks.
- El paso de revisión solo tiene la clave de IA y el de publicación solo tiene el token de GitHub.
- Los hallazgos se validan contra el diff, y se eliminan secretos, menciones, imágenes y HTML antes de publicar.
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
│   └── providers/    Proveedores de revisión Antigravity y fake
└── entrypoints/   Línea de comandos y raíz de composición
```

Para añadir un proveedor, implementa el puerto `ReviewProvider` en `adapters/providers/` y regístralo en
`entrypoints/composition.py`. No cambia nada más.

## Desarrollo

```bash
cd tools/pr-reviewer
uv sync --extra dev --extra antigravity
uv run pytest && uv run ruff check . && uv run mypy src
```

| Pruebas | Propósito | Requiere |
| --- | --- | --- |
| `tests/unit` | Reglas de dominio, casos de uso con puertos en memoria y renderizado Markdown | Nada |
| `tests/integration` | Adaptadores contra git, el sistema de archivos, una API de GitHub simulada y las clases reales del SDK | git, extra `antigravity` |
| `tests/action` | Reglas de seguridad de `action.yml` y de los workflows | Nada |
| `tests/architecture` | Regla de dependencias entre capas | Nada |

Ninguna llama a una API de pago. Los datos compartidos de prueba están en `tests/support`.

Licencia Apache-2.0.
