# Project Context: [Project Name]

- **Updated**: [YYYY-MM-DD] | Name: [...]

## 1. Stack & Entry Points
- Language(s): [...]
- Frameworks & Core Libraries: [...]
- Database / Data Storage: [...]
- Package Manager / Build Tools: [...]
- Entry points: [...]
- Config files: [...]
- Core Dependencies:
  - [...]

## 2. Directory & Layer Map
```text
[Visual tree or summary of key directories]
```
- **Domain / Business Logic**: `[paths & ownership]`
- **Interfaces / Routes / UI**: `[paths & ownership]`
- **Tests**: `[unit / integration / e2e locations]`

## 3. Run, Build & Test Commands
```bash
# Install / Setup: [command]
# Dev Server / Run: [command]
# Lint & Typecheck: [command]
# Scoped & Full Tests: [command]
```

## 4. Key Architectural & Env Invariants
- **Architecture & Layer Rules**: `[e.g., Hexagonal/Clean boundaries, state management, DI rules]`
- **Required Env Vars**: `[VAR_NAME (purpose) — never commit secrets]`
- **Root Governance Links**: Sync commands and invariants with root `AGENTS.md` (`<= 90 lines`), `DESIGN.md` (`<= 110 lines`), and `context/memory/MEMORY.md`.
