---
name: senior-architect-engineering
description: Pragmatic software architecture and system design skill. Authors concise MADR Architecture Decision Records (docs/<feature-name>/adr-NNN-*.md <= 55 lines) and the `## Architecture` section of the single discovery file docs/<feature-name>/spec.md (<= 50 lines) grounded in KISS, YAGNI, SOLID, and clean boundaries.
---

# Senior Architect Engineering Skill

## Overview
This skill guides pragmatic software architecture, structural boundary design, and technical trade-off analysis without academic boilerplate. Instead of multi-page SEI/ATAM walls of text, it enforces crisp **MADR Architecture Decision Records (`docs/<feature-name>/adr-NNN-<slug>.md`, `<= 55 lines`)** and the **`## Architecture`** section of the single discovery file **`docs/<feature-name>/spec.md`** (`<= 50 lines`) governed by KISS, YAGNI, and SOLID.

## When to Use
### Capability-Gated Trigger Rules
- **INVOKE ONLY IF** introducing genuine structural decisions: new database schemas/migrations, cross-service API contracts, new core dependencies, concurrency/resilience models, or architectural pattern shifts.
- **SKIP** when following established repository patterns, adding routine CRUD handlers/views within existing boundaries, or performing bugfixes, chores, and localized refactors.
- **Delegate Elsewhere**: Business scope & `US-XX`/`AC-XX` -> `product-analyst`; UI tokens & screens -> `ui-ux-designer`; TDD implementation -> `code-implementer`.

## Process
### 1. Right-Size the Architectural Deliverable
- **Single Structural Decision** (e.g., choosing a token store, queue strategy, or library): Author **one concise ADR (`docs/<feature-name>/adr-NNN-<slug>.md <= 55 lines`)**—keep `## Architecture` in `spec.md` to a 1–3 line pointer to it.
- **Multi-Module / Multi-Layer Feature** (touching schemas, ports/adapters, and API contracts): Author the **`## Architecture` section of `docs/<feature-name>/spec.md` (`<= 50 lines`)** defining module boundaries, data contracts, and a concise Mermaid diagram, plus an ADR only for non-obvious trade-offs.

### 2. Concise MADR Standard (`<= 55 lines`)
Follow [references/adr-template.md](references/adr-template.md) strictly—zero academic 6-part SEI/ATAM ceremony:
- **Status & Date**: `Proposed | Accepted | Superseded` — `YYYY-MM-DD`
- **`## 1. Context`**: Problem and measurable technical constraints in `<= 5 lines` (e.g., `p99 < 150ms`, idempotency).
- **`## 2. Options Considered`**: 2–3 concrete options (`1–2 lines` each).
- **`## 3. Decision & Justification`**: Chosen design, clean dependency boundaries, and why it wins under KISS/YAGNI.
- **`## 4. Trade-offs`**: `+` Benefits vs `-` Costs, operational risks, and concrete mitigations.

### 3. Clean Boundaries & Proven Tactics
- Isolate domain logic from ORM/HTTP frameworks via explicit interfaces/protocols only at real I/O seams (avoid speculative over-abstraction).
- Apply targeted resilience/performance tactics (timeouts, circuit breakers, transactional outbox, cache-aside; see [references/sei-architectural-tactics.md](references/sei-architectural-tactics.md)) only where concrete SLAs require them.
- **Shared File Rule**: If `docs/<feature-name>/spec.md` is missing, create it from the 3-heading template (`## Product`, `## Design`, `## Architecture`); edit **ONLY** `## Architecture`.
- Synchronize global `docs/architecture/` indexes if already maintained by the project.
- **Return Contract**: Final message `<= 15 lines` (status, files changed, test command + exit code or `n/a`, next step); no long narratives.

## Usage
### Commands & Scaffolding
```bash
# Optional helper to scaffold a numbered ADR from the concise MADR template
python3 ./skills/senior-architect-engineering/scripts/create_adr.py "Use Transactional Outbox for Webhooks" Proposed
```

### Example Prompts
- *"Write `docs/webhook-delivery/adr-001-outbox.md` (`<= 55 lines`) comparing synchronous HTTP vs Postgres outbox."*
- *"Define module boundaries and API schemas in the `## Architecture` section of `docs/order-checkout/spec.md` (`<= 50 lines`)."*

## Red Flags
- ❌ Mandatory academic 6-part SEI/ATAM walls of text or bloated documents (`ADR > 55 lines`, `## Architecture > 50 lines`), or a separate `architecture.md` file.
- ❌ Expanding `## Architecture` when a single `<= 55 lines` ADR suffices, or invoking architecture discovery when following existing patterns.
- ❌ Premature microservices, event buses, or speculative abstraction layers violating KISS/YAGNI.
- ❌ Ambiguous schemas, unquantified SLAs (*"fast and scalable"*), or writing production feature code directly.

## Verification
- [ ] Every ADR (`docs/<feature-name>/adr-NNN-<slug>.md`) follows [references/adr-template.md](references/adr-template.md) (`Status & Date`, `Context`, `Options Considered`, `Decision & Justification`, `Trade-offs`) and is `<= 55 lines`.
- [ ] `## Architecture` in `docs/<feature-name>/spec.md` details boundaries **only** when multiple modules/layers interact, stays strictly `<= 50 lines`, and no other section was edited.
- [ ] Domain boundaries, schemas, and invariants are concrete and ready for `code-implementer` and `compliance-verifier`.

## References
- Concise MADR Template (`<= 42 lines`): [references/adr-template.md](references/adr-template.md)
- Optional Resilience & Performance Tactics Reference: [references/sei-architectural-tactics.md](references/sei-architectural-tactics.md)
