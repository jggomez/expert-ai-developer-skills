# Workflow: Set the Quality Bar (/constraints)

**Command**: `/constraints`  
**Key Principle**: *Decide it once, enforce it everywhere*  
**Identifier**: `constraints-workflow`

---

## 1. Objective
Enforce repository and architecture constraints across security, performance budgets, formatting, branch protection, and Non-Functional Requirements (NFRs).

## 2. Operational Steps
1. **Run Static Linters & Formatters**:
   - Verify code formatting and lint rules (`ruff check`, `eslint`, `dart analyze`).
2. **Security & Secret Audit**:
   - Audit code for hardcoded secrets, tokens, private keys, or passwords.
   - Execute static security analysis (`bandit -r src/`, secret scanners).
3. **Verify NFRs & Architecture Gates**:
   - Verify compliance with architectural layer constraints (no Presentation logic in Data layer).
   - Check database access patterns (no N+1 queries, mandatory partitioning/clustering).
4. **Branch & Deployment Safety**:
   - Ensure work is on an isolated feature branch (never `main`/`master`).
   - Confirm zero unauthorized production deployment actions.

## 3. Subagent Delegation & Role Boundaries
- **Role Boundary**: The Orchestrator delegates NFR auditing, security scanning, and branch compliance to `compliance-verifier`.
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="compliance-verifier",
        prompt="Audit compliance against security, linters, and NFR gates for: <scope>"
    )
    ```
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="compliance-verifier",
        prompt="Audit compliance against security, linters, and NFR gates for: <scope>"
    )
    ```
- **Primary Skills**: `build-and-ci-gates`, `security-audit`, `compliance-verifier`, `code-smells-expert`.

## 4. Quality Gate Checklist
- [ ] Linters and formatters report 0 errors.
- [ ] Zero secrets, credentials, or private tokens in git history/diff.
- [ ] Architectural constraints and layer boundaries strictly respected.
- [ ] Explicit compliance audit verdict issued.
