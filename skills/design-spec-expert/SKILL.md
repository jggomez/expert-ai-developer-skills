---
name: design-spec-expert
description: Drafts concise Backend / API Design Specifications and Software Design Documents (docs/<feature-name>/api-spec.md or SDD <= 70 lines) before coding when introducing new endpoints, schemas, or services.
---

# Design Spec Expert Skill

## Overview
**Design Spec Expert** formalizes backend services, database schema deltas, and REST/GraphQL/gRPC contracts into a concise **Backend / API Design Spec** (`docs/<feature-name>/api-spec.md` or SDD **`<= 70 lines`**) before implementation—eliminating verbose boilerplate while preventing contract drift across **Claude Code** and **Google Antigravity**.

## When to Use
### Trigger Scenarios
- Introducing new API endpoints, request/response contracts, or cross-service integrations.
- Designing new database tables, migrations, indexes, or async worker pipelines.

### When NOT to Use
- **Changes following existing endpoints/models**: **SKIP** SDD/`api-spec.md` creation completely when changes fit established routes, schemas, or localized Tier 1 bugfixes/refactors.
- **Single architectural pattern trade-off**: Use `senior-architect-engineering` for a concise MADR (`<= 55 lines`).
- **Product user stories**: Use `product-analyst` (`docs/<feature-name>/prd.md <= 70 lines`).

## Process
1. **Check Capability Gate & Context**: Inspect root `AGENTS.md` (`<= 90 lines` wired to `context/memory/MEMORY.md`) and existing routers/models. If the task reuses existing endpoints and models, skip SDD authoring and proceed to TDD.
2. **Scaffold & Author Concise Spec (`<= 70 lines`)**: Run `create_sdd.py` or write `docs/<feature-name>/api-spec.md` directly following [references/sdd-template.md](references/sdd-template.md) across **4 crisp sections**:
   - `## 1. Objective & Scope`: Concrete problem/SLA + explicit `In Scope` / `Out of Scope` bullets.
   - `## 2. Architecture & Data Model`: Compact Mermaid flow + exact table/column/index migration delta.
   - `## 3. API Endpoints & Contracts`: Compact table (`Method & Path` | Request schema | Response schema | Status codes).
   - `## 4. Security, Edge Cases & Trade-offs`: AuthN/AuthZ, rate/input validation, idempotency/retries, and `+` Pros / `-` Risks.
3. **Gate Sign-off**: Align contracts with stakeholders (`ask_question` in Tier 2/3) and mark status `Approved` before delegating to `code-implementer`.

## Usage
### Commands & Example Prompts
```bash
python3 ./skills/design-spec-expert/scripts/create_sdd.py "Order Webhook API" Draft
```
- *"Author a concise <=70-line `docs/order-webhooks/api-spec.md` covering idempotency, DB schema delta, and status codes."*

### Host Execution
- **Claude Code / Google Antigravity**: Scaffold with `create_sdd.py` or author `docs/<feature-name>/api-spec.md` (`<= 70 lines`) directly when new contracts/schemas are introduced.

## Red Flags
- Authoring an SDD/`api-spec.md` when changes merely follow existing endpoints/models or for Tier 1 fixes.
- Exceeding **`70 lines`** or padding specs with generic prose instead of concrete schemas and status codes.
- Omitting `Out of Scope` boundaries, error status codes (`400/401/403/404/409/422`), AuthZ rules, or index definitions.

## Verification
- [ ] Capability gate verified: spec created **only** because new endpoints, schemas, or service contracts are introduced.
- [ ] Spec (`docs/<feature-name>/api-spec.md` or scaffold via `python3 ./skills/design-spec-expert/scripts/create_sdd.py "<Title>"`) is **`<= 70 lines`**.
- [ ] Contains all 4 canonical sections (`Objective & Scope`, `Architecture & Data Model`, `API Endpoints & Contracts`, `Security, Edge Cases & Trade-offs`) with valid Mermaid syntax.

## References
- [Concise Backend / API Design Spec Template](references/sdd-template.md)
