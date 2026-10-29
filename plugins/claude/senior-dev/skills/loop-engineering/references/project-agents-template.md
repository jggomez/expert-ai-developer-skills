# AGENTS.md — [Project Name]

## 1. Project Overview & Tech Stack
<3–5 lines summarizing what this application/service does, its primary runtime/language (e.g., Python 3.12 + FastAPI, TypeScript + Next.js, Flutter 3.x), database/storage layer, and deployment target.>

## 2. Executable Commands
- **Install**: `<e.g., uv sync | npm ci | flutter pub get>`
- **Dev**: `<e.g., uv run uvicorn src.main:app --reload | npm run dev>`
- **Test**: `<e.g., uv run pytest tests/ -v | npm test | flutter test>`
- **Lint / Typecheck**: `<e.g., uv run ruff check . && uv run mypy src/ | npm run lint && npm run typecheck>`
- **Build**: `<e.g., npm run build | flutter build appbundle>`

## 3. Architecture & Coding Conventions
- **Directory Layout**:
  - `src/` (or `lib/`): Core domain, application services, and HTTP/UI adapters.
  - `tests/`: `unit/`, `integration/`, and `e2e/` suites mirroring source modules.
  - `docs/<feature-name>/`: Concise feature artifacts (`prd.md <= 70 lines`, `adr-NNN-*.md <= 55 lines`, `test-matrix.md <= 80 lines`).
- **Key Invariants**:
  - Keep domain logic decoupled from database/HTTP frameworks at module boundaries (SOLID / KISS / YAGNI).
  - Never commit directly to `main`/`master`/`develop`; use Conventional Commits on `feat/<slug>` or `fix/<slug>` branches.
  - Require empirical `exit code 0` test proof before marking any task complete.

## 4. Design & Persistent Memory
- **UI Design System (`DESIGN.md`)**: When building or modifying UI, read root [DESIGN.md](./DESIGN.md) (`<= 110 lines`, official Google 2-layer YAML + 8-section spec) for semantic color, typography, spacing, and component tokens; keep feature UI deltas in `docs/<feature-name>/design.md` (`<= 35 lines`).
- **Cross-Session AI Memory (`context/memory/`)**:
  - Silently read [context/memory/MEMORY.md](./context/memory/MEMORY.md) at session start to restore active handoff state across Claude Code and Antigravity.
  - Consult [context/memory/architecture.md](./context/memory/architecture.md), [context/memory/conventions.md](./context/memory/conventions.md), and daily logs in `context/memory/log/YYYY-MM-DD.md` on demand, and update them in-place upon milestone completion.
