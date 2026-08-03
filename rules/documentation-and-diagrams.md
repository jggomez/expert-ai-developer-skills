---
trigger: model_decision
description: Enforce documentation standards for code comments, docstrings, README files, project context, and Mermaid architecture diagrams.
---

# Rule: Documentation & Diagram Integrity

**Identifier**: `documentation-and-diagrams`

## 1. Code-Level Documentation Directives

* **MUST** update docstrings and signature annotations immediately when modifying functions or classes.
* **MUST** preserve existing, unrelated docstrings and file header comments.
* **NEVER** write redundant comments stating what code self-evidently does. Comments **MUST** explain *why*.
* **MUST** delete obsolete comments invalidated by code refactoring.

## 2. READMEs & Mermaid Diagram Rules

* **MUST** update `README.md` files when adding features, API routes, or environment setup dependencies.
* **MUST** update `mermaid` architecture/sequence diagrams when altering component structures.
* **Mermaid Syntax**: **NEVER** use HTML tags inside nodes. **MUST** quote labels with special chars: `id["Label (info)"]`.

## 3. Schema & API Documentation

* **MUST** keep Pydantic schemas and OpenAPI documentation in sync with API route modifications.
* **MUST** include clear migration descriptions in database versioning scripts (e.g. Alembic).
