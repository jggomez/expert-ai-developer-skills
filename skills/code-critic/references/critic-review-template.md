# Critic Code Review Report

## Executive Summary
- **Feature Name**: `<feature-name>`
- **Reviewer**: `critic` (Independent Code Review Specialist)
- **Review Date**: `YYYY-MM-DD`
- **Git Commit / Diff Ref**: `HEAD`
- **Overall Verdict**: `[PASSED | CONDITIONAL PASS | REJECTED]`
- **Overall Quality Score**: `[Score]/30 ([Percentage]%)`

---

## 1. Quality Scoring Rubric

| Dimension | Weight | Max Points | Score (1-5) | Weighted Score | Notes & Findings |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Cyclomatic Complexity & Control Flow** | 20% | 5 | `[1-5]` | `[X.X]` | Nesting depth <= 3, CC <= 10 per method |
| **2. DRY & Duplication Elimination** | 15% | 5 | `[1-5]` | `[X.X]` | Reusable logic, zero copy-paste routines |
| **3. SOLID Principles Adherence** | 25% | 5 | `[1-5]` | `[X.X]` | SRP, OCP, LSP, ISP, and DIP invariants |
| **4. Architectural Anti-Patterns & Code Smells** | 15% | 5 | `[1-5]` | `[X.X]` | No God Classes, Feature Envy, or Primitive Obsession |
| **5. Maintainability & Cognitive Load** | 10% | 5 | `[1-5]` | `[X.X]` | Concise functions, clean English names, self-documenting |
| **6. Interface Robustness & Error Handling** | 15% | 5 | `[1-5]` | `[X.X]` | Type safety, input boundaries, zero swallowed errors |
| **Total** | **100%** | **30** | — | **[Total]/30** | **Final Quality Percentage: [XX]%** |

### Verdict Thresholds
- **PASSED** (Score >= 85%, no dimension < 3): Code meets high architectural and maintainability standards; ready for merge.
- **CONDITIONAL PASS** (Score 70% - 84%, no dimension < 2): Non-blocking technical debt detected; minor remediation recommended.
- **REJECTED** (Score < 70% OR any dimension = 1 OR critical blocker): Must be remediated by `code-implementer` prior to release.

---

## 2. Detailed Dimension Breakdown

### 2.1. Cyclomatic Complexity & Control Flow
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - `path/to/file.py:45`: Function `process_transaction` has CC = 14 (Threshold: <= 10) and nesting depth 4.
- **Remediation**: Extract conditional branches into helper functions or strategy map.

### 2.2. DRY (Don't Repeat Yourself) & Duplication
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - `path/to/file_a.py:112` and `path/to/file_b.py:87`: Duplicated payload validation logic.
- **Remediation**: Extract common validation helper into shared domain validator.

### 2.3. SOLID Principles Adherence
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - **Single Responsibility (SRP)**:
  - **Open/Closed (OCP)**:
  - **Liskov Substitution (LSP)**:
  - **Interface Segregation (ISP)**:
  - **Dependency Inversion (DIP)**:

### 2.4. Architectural Anti-Patterns & Code Smells
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - Identified smells categorized via Fowler/Beck taxonomy.

### 2.5. Maintainability & Cognitive Load
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - Naming conventions, function sizing, comment clarity, and cognitive flow.

### 2.6. Interface Robustness & Error Handling
- **Status**: `[Clean | Needs Attention | Blocking]`
- **Findings**:
  - Parameter typing, nullability, boundary checks, and exception propagation.

---

## 3. Prioritized Action Items for `code-implementer`

| Priority | Dimension | File & Line | Issue Summary | Required Remediation |
| :---: | :---: | :--- | :--- | :--- |
| **P0 (Blocker)** | SOLID / SRP | `src/services/billing.py:120` | God method mixing DB calls, PDF gen, and email | Split into dedicated service classes |
| **P1 (High)** | Complexity | `src/utils/parser.py:55` | Nested loops with cyclomatic complexity 12 | Flatten with generator expressions |
| **P2 (Medium)** | Robustness | `src/api/routes.py:80` | Swallowed `Exception` without logging traceback | Log and return structured error response |
| **P3 (Low)** | Clean Code | `src/models/user.py:34` | Ambiguous variable name `tmp_lst` | Rename to `active_session_ids` |
