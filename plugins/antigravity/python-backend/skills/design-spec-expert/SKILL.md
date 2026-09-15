---
name: design-spec-expert
description: Coordinates system specifications and drafts detailed Software Design Documents (SDD) before coding. Use this skill when asked to plan large architectural changes, write system design documents, or establish design specifications for a new service.
---

# Design Spec Expert Skill

## Overview
This skill guides the formalization of technical architectures and subsystem specifications into Software Design Documents (SDD). It acts as a Pragmatic Systems Designer, ensuring that system boundaries, component diagrams, database schemas, API contracts, and deployment strategies are completely specified and reviewed before implementation begins, preventing architectural drift and compounding technical debt.

## When to Use
### Trigger Scenarios
- Planning major features, new microservices, or complex subsystem redesigns.
- Authoring comprehensive Software Design Documents (SDDs) for engineering review.
- Specifying database schemas, ER diagrams, and REST/GraphQL/gRPC interface contracts.
- Establishing test strategies, rollback plans, and deployment blueprints prior to coding.

### When NOT to Use
- **Informal architectural decisions or single pattern choices**: Route to `senior-architect-engineering` for an ADR.
- **Product discovery and user requirement gathering**: Route to `product-analyst` for a PRD.
- **Immediate bug fixing or small utility code**: Route to `code-implementer`.
- **Repository codebase indexing**: Route to `repo-research`.

## Process
### Phase 1: Requirements Gathering & System Context
1. Ingest product requirements (PRD) and business goals.
2. Formulate explicit technical assumptions, operational constraints, and quality attributes.
3. Identify external integrations, legacy dependencies, and cross-cutting security boundaries.

### Phase 2: SDD Generation & Scaffolding
1. Bootstrap the design document using the automated SDD generation script:
   ```bash
   python3 ./skills/design-spec-expert/scripts/create_sdd.py "<System Title>" [Draft/Review/Approved]
   ```
2. Open the generated markdown document and populate all core sections referencing the template:
   - **Executive Summary & Scope**: Clear description of deliverables and explicit *out-of-scope* items.
   - **Component Architecture**: Mermaid diagrams detailing component interactions and data flows.
   - **Data Model & Schema**: Table schemas, indexes, foreign keys, and migration strategy.
   - **API Contracts**: Detailed endpoint specs (methods, paths, request/response models, status codes).
   - **Testing & Deployment Strategy**: Coverage goals, hermetic testing boundaries, canary/blue-green plans.

### Phase 3: Engineering Review & Gate Sign-off
1. Present the SDD to stakeholders or peer agents for technical critique.
2. Resolve identified edge cases and update status from `Draft` to `Review` or `Approved`.

## Usage
### Commands & Automation Scripts
```bash
# Generate a new Software Design Document
python3 ./skills/design-spec-expert/scripts/create_sdd.py "User Notification Service" Draft
```

### Example Prompts
- *"Scaffold an SDD for our new payment gateway integration, covering API specs and database schemas."*
- *"Draft a software design document for an asynchronous video transcoding worker system."*
- *"Prepare a detailed technical specification for migrating user session storage to Redis."*

### Host Execution Instructions
- **Claude Code**: Execute `create_sdd.py` in the workspace shell, then edit the generated markdown file.
- **Antigravity**: Launch as the design lead to produce the design specification artifact before delegating build tasks.

## Red Flags
- Commencing implementation before the SDD is approved or core contracts are finalized.
- Omission of explicit *Out-of-Scope* boundaries, resulting in scope creep.
- Hand-waving API contracts (e.g. omitting error schemas or status codes).
- Drafting an excessively heavyweight SDD for a trivial localized bug fix.

## Verification
- [ ] SDD file created using the automation script:
  ```bash
  python3 ./skills/design-spec-expert/scripts/create_sdd.py "<Title>"
  ```
- [ ] Architecture diagrams rendered with valid Mermaid syntax.
- [ ] Database schemas and index strategies documented.
- [ ] API endpoints defined with request/response payloads.
- [ ] Testing and rollout rollback plan articulated.

## References
For the standardized document layout and section definitions:
- [SDD Template Reference](references/sdd-template.md)

