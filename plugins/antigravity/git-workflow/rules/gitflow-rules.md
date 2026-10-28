---
trigger: always_on
description: Gitflow engineering rules enforcing branch protection, automatic feature branch provisioning, proactive scope drift detection via ask_question, Conventional Commits standards, and working tree cleanliness.
---

# Gitflow Workflow Rules & Commit Standards

**Identifier**: `gitflow-rules`

## 1. Branch Protection & Automatic Feature Branch Provisioning
- **Protected Base Branches**: `main`, `master`, `develop`, and `dev` represent stable release and integration environments. Committing, staging, or pushing directly to these branches is **STRICTLY PROHIBITED**.
- **Auto-Branching Gate at State 0**:
  - Upon receiving any task, the agent/orchestrator must inspect the active git branch (`git symbolic-ref --short HEAD`).
  - If the active branch is a protected base branch, the agent **MUST** automatically provision a dedicated feature branch using Conventional naming (`feat/<descriptive-slug>`, `fix/<descriptive-slug>`, `refactor/<slug>`) and switch to it (`git checkout -b <type>/<slug>`).
  - Notify the user of the new branch creation. Never perform implementation or file modifications while on a protected base branch.
- **Merge Invariant**: Code enters `main` or `develop` exclusively through reviewed and validated Pull Requests with passing CI checks.

## 2. Proactive Scope Drift Detection
- **Scope Drift Detection**: When already operating on an active feature branch, if incoming user requests introduce orthogonal, unrelated, or distinct domain functionality outside the active branch scope, the agent **MUST NOT** blindly accumulate unrelated changes on the branch.
- **Interactive Scope Drift Modal (`ask_question`)**:
  - The orchestrator/agent must proactively pause and present an interactive GUI modal via `ask_question`.
  - Present the user with explicit options:
    1. Create and switch to a new dedicated branch (e.g. `feat/<new-slug>`) for the new scope.
    2. Continue on the current branch (user explicitly confirming scope expansion).
  - Await explicit user selection before executing changes.

## 3. Conventional Commits Standards
- Every commit message must strictly follow the Conventional Commits specification:
  ```
  <type>(<optional scope>): <description>

  [optional body]

  [optional footer(s)]
  ```
- **Rules**:
  - Description must be in imperative mood, lowercase, with no trailing period (e.g. `feat(auth): implement token refresh rotation`).
  - Optional body explains the context and reasoning for non-trivial modifications.
- **Allowed Types**:
  - `feat`: A new feature for the user or system consumer.
  - `fix`: A bug fix.
  - `refactor`: Code change that neither fixes a bug nor adds a feature.
  - `test`: Adding missing tests or correcting existing tests.
  - `docs`: Documentation only changes.
  - `chore`: Build process, auxiliary tools, or dependency maintenance.
  - `perf`: A code change that improves performance or latency.
  - `build`: Changes affecting build systems, packaging, or external dependencies.
  - `ci`: Changes to CI configuration files and automation scripts.

## 4. Working Tree Cleanliness & Merge Safety Invariants
- **Atomic Staging**: Stage files selectively and deliberately (`git add <file1> <file2>`). **NEVER** run blanket `git add .` on dirty workspaces to prevent staging scratch files, temporary logs, or credentials.
- **Merge Conflict Ban**: Never complete a session leaving uncommitted merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) or unresolved merge states (`UU`, `AA`). All conflicts must be resolved cleanly.
- **Clean Workspace Invariant**: Ensure no unexpected unstaged modifications, uncommitted WIP files, or dangling rebase states remain at session conclusion without explicit user instruction.
