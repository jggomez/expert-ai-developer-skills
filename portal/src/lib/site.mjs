/**
 * Shared site data: languages, item kinds, UI strings and the orchestrator pipeline.
 * Plain ESM so Astro pages and vitest read the same source.
 */
import catalog from '../data/catalog.json' with { type: 'json' };
import en from '../i18n/en.json' with { type: 'json' };
import es from '../i18n/es.json' with { type: 'json' };

export const LANGS = ['es', 'en'];
export const DEFAULT_LANG = 'es';
export const SITE_URL = 'https://senior-ai-dev-kit.web.app';
export const REPO_URL = `https://github.com/${catalog.repo}`;

/** Display order of kinds; also the order of filter chips. */
export const KINDS = ['plugin', 'agent', 'skill', 'hook', 'rule', 'workflow', 'sidecar', 'tool'];

const ITEMS = { es: es.items, en: en.items };

export const UI = {
  es: {
    htmlTitle: 'Senior AI Dev Kit: agentes, skills y plugins',
    metaDescription: 'Catálogo en español e inglés de los plugins, subagentes, skills, rules, workflows y hooks del Senior AI Dev Kit para Claude Code y Google Antigravity.',
    nav: { tools: 'Herramientas', catalog: 'Catálogo', flow: 'Cómo trabaja', install: 'Instalar', source: 'Código en GitHub' },
    toolsTitle: 'Dos herramientas que puedes usar hoy',
    toolsLead: 'No necesitan ningún plugin. Instálalas solas y empieza a medir y revisar.',
    howToInstall: 'Cómo instalarla',
    screens: 'Pantallas',
    openImage: 'Ver imagen completa',
    closeImage: 'Cerrar',
    moreAbout: 'Ver detalles',
    guides: 'Guías',
    switchTo: 'English',
    heroTitle: 'Un equipo de agentes que planea antes de programar y demuestra lo que hizo.',
    heroLead: 'Plugins, subagentes y skills para Claude Code y Google Antigravity. Un orquestador clasifica cada tarea por riesgo, delega en especialistas y solo da algo por terminado cuando las pruebas pasan.',
    flowTitle: 'Cómo trabaja una tarea',
    flowLead: 'Elige una fase para ver qué agentes, skills, hooks y workflows participan en ella.',
    insideTitle: 'Qué trae el kit',
    catalogTitle: 'Catálogo',
    searchLabel: 'Buscar en el catálogo',
    searchPlaceholder: 'Busca por nombre o tema: pruebas, SQL, Flutter…',
    allKinds: 'Todo',
    hostLabel: 'Herramienta',
    hostAll: 'Ambas',
    results: (n) => (n === 1 ? '1 resultado' : `${n} resultados`),
    empty: 'Nada coincide con esa búsqueda. Prueba con otra palabra o quita los filtros.',
    clearFilters: 'Quitar filtros',
    installTitle: 'Instalar',
    installLead: 'Agrega el marketplace una vez e instala el plugin que necesites. Las dependencias se instalan solas.',
    installClaude: 'Claude Code',
    installAntigravity: 'Google Antigravity',
    installSkills: 'Una skill suelta, en cualquier repo',
    copy: 'Copiar',
    copied: 'Copiado',
    whenToUse: 'Cuándo usarlo',
    howToGet: 'Cómo obtenerlo',
    includedIn: 'Viene en',
    contains: 'Incluye',
    original: 'Descripción técnica (en inglés)',
    viewSource: 'Ver el código fuente',
    backToCatalog: 'Volver al catálogo',
    model: 'Modelo',
    schedule: 'Horario',
    command: 'Comando',
    hosts: 'Funciona en',
    viaPlugin: (p) => `Se instala con el plugin ${p}.`,
    copyFile: 'Copia el archivo a tu repo o instálalo con el plugin de tu herramienta.',
    notFoundTitle: 'Esta página no existe',
    notFoundLead: 'Puede que el enlace sea viejo. Vuelve al catálogo y búscalo por nombre.',
    footer: 'Código abierto con licencia Apache 2.0.',
    shortcut: 'Pulsa / para buscar',
  },
  en: {
    htmlTitle: 'Senior AI Dev Kit: agents, skills and plugins',
    metaDescription: 'Catalog in English and Spanish of the Senior AI Dev Kit plugins, subagents, skills, rules, workflows and hooks for Claude Code and Google Antigravity.',
    nav: { tools: 'Tools', catalog: 'Catalog', flow: 'How it works', install: 'Install', source: 'Code on GitHub' },
    toolsTitle: 'Two tools you can use today',
    toolsLead: 'They need no plugin. Install them on their own and start measuring and reviewing.',
    howToInstall: 'How to install it',
    screens: 'Screens',
    openImage: 'View full image',
    closeImage: 'Close',
    moreAbout: 'See details',
    guides: 'Guides',
    switchTo: 'Español',
    heroTitle: 'A team of agents that plans before it codes and proves what it did.',
    heroLead: 'Plugins, subagents and skills for Claude Code and Google Antigravity. An orchestrator sizes each task by risk, delegates to specialists and only calls something done when the tests pass.',
    flowTitle: 'How a task moves',
    flowLead: 'Pick a phase to see which agents, skills, hooks and workflows take part in it.',
    insideTitle: 'What the kit includes',
    catalogTitle: 'Catalog',
    searchLabel: 'Search the catalog',
    searchPlaceholder: 'Search by name or topic: tests, SQL, Flutter…',
    allKinds: 'All',
    hostLabel: 'Tool',
    hostAll: 'Both',
    results: (n) => (n === 1 ? '1 result' : `${n} results`),
    empty: 'Nothing matches that search. Try another word or clear the filters.',
    clearFilters: 'Clear filters',
    installTitle: 'Install',
    installLead: 'Add the marketplace once, then install the plugin you need. Dependencies install on their own.',
    installClaude: 'Claude Code',
    installAntigravity: 'Google Antigravity',
    installSkills: 'A single skill, in any repo',
    copy: 'Copy',
    copied: 'Copied',
    whenToUse: 'When to use it',
    howToGet: 'How to get it',
    includedIn: 'Comes with',
    contains: 'Includes',
    original: 'Technical description',
    viewSource: 'View the source',
    backToCatalog: 'Back to the catalog',
    model: 'Model',
    schedule: 'Schedule',
    command: 'Command',
    hosts: 'Works in',
    viaPlugin: (p) => `Installed with the ${p} plugin.`,
    copyFile: 'Copy the file into your repo, or install it with your tool’s plugin.',
    notFoundTitle: 'This page does not exist',
    notFoundLead: 'The link may be old. Go back to the catalog and search for it by name.',
    footer: 'Open source under the Apache 2.0 license.',
    shortcut: 'Press / to search',
  },
};

export const KIND_LABELS = {
  es: {
    plugin: ['plugin', 'plugins'],
    agent: ['subagente', 'subagentes'],
    skill: ['skill', 'skills'],
    hook: ['hook', 'hooks'],
    rule: ['rule', 'rules'],
    workflow: ['workflow', 'workflows'],
    sidecar: ['sidecar', 'sidecars'],
    tool: ['herramienta', 'herramientas'],
  },
  en: {
    plugin: ['plugin', 'plugins'],
    agent: ['subagent', 'subagents'],
    skill: ['skill', 'skills'],
    hook: ['hook', 'hooks'],
    rule: ['rule', 'rules'],
    workflow: ['workflow', 'workflows'],
    sidecar: ['sidecar', 'sidecars'],
    tool: ['tool', 'tools'],
  },
};

export const KIND_BLURBS = {
  es: {
    plugin: 'Paquetes que se instalan de una vez: agentes, skills, hooks y servidores MCP.',
    agent: 'Especialistas a los que el orquestador delega cada parte del trabajo.',
    skill: 'Instrucciones expertas en el formato abierto Agent Skills.',
    hook: 'Controles que corren solos y no dependen de que el modelo se acuerde.',
    rule: 'Reglas cortas y estrictas que todo agente sigue.',
    workflow: 'Guiones paso a paso como /spec, /plan, /review y /ship.',
    sidecar: 'Tareas en segundo plano o programadas para Antigravity.',
    tool: 'Herramientas independientes que no necesitan plugin.',
  },
  en: {
    plugin: 'Bundles you install in one step: agents, skills, hooks and MCP servers.',
    agent: 'Specialists the orchestrator delegates each part of the work to.',
    skill: 'Expert instructions in the open Agent Skills format.',
    hook: 'Checks that run on their own instead of relying on the model to remember.',
    rule: 'Short, strict rules every agent follows.',
    workflow: 'Step-by-step playbooks such as /spec, /plan, /review and /ship.',
    sidecar: 'Background and scheduled tasks for Antigravity.',
    tool: 'Standalone tools that need no plugin.',
  },
};

export const HOST_LABELS = { claude: 'Claude Code', antigravity: 'Antigravity' };

/** The orchestrator pipeline; each phase lists the catalog ids active in it. */
export const PIPELINE = [
  {
    key: 'triage',
    name: { es: 'Clasificar', en: 'Triage' },
    text: {
      es: 'Lee la memoria del proyecto, escribe el PLAN.md y decide el nivel: rápido, estándar o crítico. Según el nivel llama a más o menos especialistas.',
      en: 'Reads the project memory, writes PLAN.md and picks the tier: fast-track, standard or mission-critical. The tier decides how many specialists are called.',
    },
    ids: ['agent/senior-dev-orchestrator', 'agent/flutter-feature-orchestrator', 'agent/python-backend-orchestrator', 'skill/loop-engineering', 'skill/context-restore', 'hook/session-start-context', 'workflow/plan-workflow'],
  },
  {
    key: 'discovery',
    name: { es: 'Descubrir', en: 'Discover' },
    text: {
      es: 'Solo si hace falta: producto aclara el alcance, diseño define pantallas y arquitectura registra decisiones. Luego te pide aprobación antes de programar.',
      en: 'Only when needed: product clarifies scope, design defines screens and architecture records decisions. Then it asks for your approval before any code.',
    },
    ids: ['agent/product-analyst', 'agent/ui-ux-designer', 'agent/architect-engineer', 'agent/flutter-architect', 'workflow/spec-workflow', 'workflow/grill-me-alignment-workflow', 'skill/design-spec-expert'],
  },
  {
    key: 'build',
    name: { es: 'Construir', en: 'Build' },
    text: {
      es: 'Uno o varios implementadores trabajan en paralelo, cada uno en sus propios archivos, siempre con una prueba que falla primero.',
      en: 'One or more implementers work in parallel, each in its own files, always starting from a failing test.',
    },
    ids: ['agent/code-implementer', 'agent/flutter-implementer', 'skill/test-driven-development', 'hook/orchestrator-role-gate', 'hook/pre-tool-gate', 'hook/flutter-pre-tool-gate', 'workflow/build-workflow'],
  },
  {
    key: 'verify',
    name: { es: 'Verificar', en: 'Verify' },
    text: {
      es: 'QA corre las pruebas y exige exit code 0. En cambios de riesgo se suman crítico, retador y pruebas en navegador con capturas reales.',
      en: 'QA runs the tests and requires exit code 0. Risky changes add the critic, the challenger and browser tests with real screenshots.',
    },
    ids: ['agent/qa-tester', 'agent/compliance-verifier', 'agent/critic', 'agent/challenger', 'agent/e2e-blackbox-tester', 'agent/flutter-reviewer', 'hook/e2e-evidence-gate', 'hook/universal-quality-gate', 'workflow/review-workflow'],
  },
  {
    key: 'ship',
    name: { es: 'Entregar', en: 'Ship' },
    text: {
      es: 'Marca el plan como completo, guarda lo aprendido en la memoria compartida y hace un commit convencional en su propia rama.',
      en: 'Marks the plan complete, saves what was learned to the shared memory and makes a conventional commit on its own branch.',
    },
    ids: ['skill/context-capture', 'agent/context-keeper', 'hook/gitflow-branch-gate', 'hook/stop-flush', 'workflow/commit-workflow', 'skill/pull-request-expert', 'workflow/ship-workflow'],
  },
];

export const catalogItems = catalog.items;
export const counts = catalog.counts;
export const marketplace = catalog.marketplace;
export const repoSlug = catalog.repo;

const byId = new Map(catalog.items.map((item) => [item.id, item]));

export function getItem(id) {
  return byId.get(id);
}

/** Curated, translated text for an item id. Throws when a translation is missing. */
export function itemText(lang, id) {
  const text = ITEMS[lang]?.[id];
  if (!text) throw new Error(`Missing ${lang} translation for ${id}`);
  return text;
}

export function translations(lang) {
  return ITEMS[lang];
}

export function itemUrl(lang, item) {
  return `/${lang}/${item.type}/${item.slug}/`;
}

/** The same page in the other language. */
export function swapLangPath(path, lang) {
  const other = lang === 'es' ? 'en' : 'es';
  return path.replace(new RegExp(`^/${lang}(/|$)`), `/${other}$1`);
}

export function kindLabel(lang, kind, n = 1) {
  const [one, many] = KIND_LABELS[lang][kind];
  return n === 1 ? one : many;
}

const RELEASE = `${REPO_URL}/releases/download/agent-meter-v0.1.0`;
const TREE = `${REPO_URL}/blob/main`;

/**
 * Standalone tools shown in the home showcase and on their detail pages.
 * `screens` lists screenshot ids (file name without `-es`) in display order; captions are per language.
 */
export const TOOLS = {
  'agent-meter': {
    tagline: {
      es: 'Cuánto cuestan tus agentes y cuánto tardan, por proyecto, tarea y subagente.',
      en: 'What your agents cost and how long they take, per project, task and subagent.',
    },
    screens: [
      { id: 'app-live', name: { es: 'En vivo', en: 'Live' }, caption: { es: 'Gasto de hoy y del mes, previsión, presupuestos y sesiones activas.', en: 'Spend today and this month, forecast, budgets and active sessions.' } },
      { id: 'app-history', name: { es: 'Historial', en: 'History' }, caption: { es: 'Costo y tiempo por día, proyecto y modelo.', en: 'Cost and time per day, project and model.' } },
      { id: 'app-insights', name: { es: 'Insights', en: 'Insights' }, caption: { es: 'Qué está encareciendo tus tareas y qué cambiar.', en: 'What is making your tasks expensive and what to change.' } },
      { id: 'app-changes', name: { es: 'Cambios', en: 'Changes' }, caption: { es: 'Ajustes que propone, que tú confirmas y puedes deshacer.', en: 'Setting changes it suggests, which you confirm and can undo.' } },
      { id: 'app-projects', name: { es: 'Proyectos', en: 'Projects' }, caption: { es: 'Cada proyecto con su costo, sesiones y presupuesto.', en: 'Each project with its cost, sessions and budget.' } },
      { id: 'app-settings', name: { es: 'Ajustes', en: 'Settings' }, caption: { es: 'Idioma, presupuestos, hosts y modo local o en la nube.', en: 'Language, budgets, hosts and local or cloud mode.' } },
    ],
    downloads: [
      { label: { es: 'Descargar para Mac', en: 'Download for Mac' }, detail: { es: 'Apple Silicon, .dmg', en: 'Apple Silicon, .dmg' }, href: `${RELEASE}/agent-meter-0.1.0-mac-arm64.dmg` },
      { label: { es: 'Descargar para Windows', en: 'Download for Windows' }, detail: { es: 'Windows 10 y 11, .exe', en: 'Windows 10 and 11, .exe' }, href: `${RELEASE}/agent-meter-0.1.0-windows-x64.exe` },
    ],
    unsigned: {
      es: 'La app no está firmada. En Mac: Ajustes del Sistema, Privacidad y seguridad, “Abrir igualmente”. En Windows: “Más información” y “Ejecutar de todas formas”.',
      en: 'The app is not signed. On Mac: System Settings, Privacy & Security, “Open Anyway”. On Windows: “More info”, then “Run anyway”.',
    },
    steps: [
      { text: { es: 'O instala la línea de comandos con la app incluida:', en: 'Or install the command line with the app included:' }, command: 'uv tool install --python 3.12 "agent-meter[app] @ git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"' },
      { text: { es: 'Configúralo en modo local, sin nube:', en: 'Set it up in local mode, no cloud needed:' }, command: 'agent-meter setup --local' },
      { text: { es: 'Abre la app:', en: 'Open the app:' }, command: 'agent-meter app' },
    ],
    guides: [
      { label: { es: 'Guía completa', en: 'Full guide' }, href: { es: `${TREE}/tools/agent-meter/README.es.md`, en: `${TREE}/tools/agent-meter/README.md` } },
      { label: { es: 'Guía de la app', en: 'App guide' }, href: { es: `${TREE}/tools/agent-meter/docs/app-guide.es.md`, en: `${TREE}/tools/agent-meter/docs/app-guide.md` } },
    ],
  },
  'pr-reviewer': {
    tagline: {
      es: 'Un revisor con IA en cada pull request, que comenta y propone el arreglo sin bloquear el merge.',
      en: 'An AI reviewer on every pull request that comments and proposes the fix without blocking the merge.',
    },
    screens: [
      { id: 'inline-comment-sql-injection', name: { es: 'Comentario en línea', en: 'Inline comment' }, caption: { es: 'Encuentra una inyección SQL y propone el código corregido en la misma línea.', en: 'Finds a SQL injection and proposes the fixed code on that line.' } },
      { id: 'summary-comment', name: { es: 'Resumen', en: 'Summary' }, caption: { es: 'Un resumen del pull request con los hallazgos ordenados por gravedad.', en: 'A pull request summary with findings sorted by severity.' } },
      { id: 'summary-change-map', name: { es: 'Mapa de cambios', en: 'Change map' }, caption: { es: 'Un resumen técnico del cambio y un diagrama de las áreas tocadas, coloreadas por su hallazgo más grave.', en: 'A technical summary of the change and a diagram of the areas it touches, colored by their worst finding.' } },
      { id: 'inline-comment-command-injection', name: { es: 'Inyección de comandos', en: 'Command injection' }, caption: { es: 'Detecta comandos de shell armados con datos no confiables.', en: 'Flags shell commands built from untrusted input.' } },
    ],
    downloads: [],
    unsigned: null,
    steps: [
      { text: { es: 'Desde la raíz de tu repositorio, agrega el workflow fijado al último commit:', en: 'From the root of your repository, add the workflow pinned to the latest commit:' }, command: 'mkdir -p .github/workflows && SHA=$(git ls-remote https://github.com/jggomez/expert-ai-developer-skills refs/heads/main | cut -f1) && curl -fsSL https://raw.githubusercontent.com/jggomez/expert-ai-developer-skills/main/tools/pr-reviewer/examples/pr-review.yml | sed "s/<commit-sha>/$SHA/" > .github/workflows/pr-review.yml' },
      { text: { es: 'Crea una API key de Gemini y guárdala en Settings, Secrets and variables, Actions como GEMINI_API_KEY.', en: 'Create a Gemini API key and save it under Settings, Secrets and variables, Actions as GEMINI_API_KEY.' }, command: null },
      { text: { es: 'Haz merge del workflow y abre un pull request. En unos minutos llegan los comentarios.', en: 'Merge the workflow and open a pull request. Comments arrive in a few minutes.' }, command: null },
    ],
    guides: [
      { label: { es: 'Guía completa', en: 'Full guide' }, href: { es: `${TREE}/tools/pr-reviewer/README.es.md`, en: `${TREE}/tools/pr-reviewer/README.md` } },
      { label: { es: 'Usar Claude en vez de Gemini', en: 'Use Claude instead of Gemini' }, href: { es: `${TREE}/tools/pr-reviewer/docs/guide.es.md`, en: `${TREE}/tools/pr-reviewer/docs/guide.md` } },
    ],
  },
};

/** The screenshot of `screen` for `lang`, falling back to English when there is no Spanish version. */
export function screenMedia(item, screen, lang) {
  const media = item.media ?? [];
  return media.find((m) => m.screen === screen && m.lang === lang) ?? media.find((m) => m.screen === screen && m.lang === 'en');
}
