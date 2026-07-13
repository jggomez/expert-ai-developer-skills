# Rule: Documentation & Diagram Integrity

**Identifier**: `documentation-and-diagrams`  
**Purpose**: Ensure API specs, setup manuals, code comments, and Mermaid architecture diagrams are updated concurrently with code changes, preventing stale documentation.

---

## 1. Code-Level Documentation

* **Docstring Integrity**: When modifying a function, class, or method, immediately update its docstring/comments to match the new signature and behavior. Preserve docstrings and comments that are unrelated to your edits.
* **Remove Outdated Comments**: If refactoring code makes an existing comment obsolete or incorrect, delete or rewrite it. Do not leave confusing, obsolete explanations in the code.
* **Inline Comments**: Write inline comments only for complex, non-obvious algorithms or business rules. Obvious code does not need comments.

---

## 2. Project READMEs & Architecture Diagrams

* **Update READMEs**: If you introduce a new feature, a new API endpoint, or modify installation prerequisites, update the relevant `README.md` in the directory or at the workspace root.
* **Mermaid Diagram Updates**: If class relations, sequence flows, or deployment architectures change, identify the corresponding `mermaid` block in the documentation and update the nodes and relationships.
* **Mermaid Syntax Rules**:
  * Never use HTML tags inside nodes.
  * Quote node labels if they contain parenthesis, brackets, or commas to prevent renderer parsing errors (e.g., `id["Label (info)"]`).

---

## 3. API & Schema Specification

* **FastAPI / OpenAPI Docs**: When changing request/response schemas or endpoint paths, update the corresponding Pydantic schemas and API descriptions. Ensure that documentation generators (like Swagger/ReDoc) display correct details.
* **Database Schema Migration Notes**: Write descriptive notes in your migrations (e.g., Alembic migrations) explaining the exact schema modification and table changes.
