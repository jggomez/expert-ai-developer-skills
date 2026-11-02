# Critic Code Review Report

> **Zero-Fluff Cap (`<= 50 lines` max, `<= 20 lines` on clean pass)**: Output ONLY the metadata header, 6-dimension rubric table, and actionable defects. Omit all prose sections. On a clean `PASSED` review, replace the Actionable Defects table with `None.`

- **Feature**: `<feature-name>` | **Date**: `YYYY-MM-DD` | **Diff Ref**: `HEAD`
- **Reviewer**: `critic` | **Verdict**: `[PASSED | CONDITIONAL PASS | REJECTED]` | **Score**: `[XX.X]/30 ([XX]%)`

## 1. Quality Scoring Summary

| Dimension | Weight | Score (1-5) | Weighted | Key Metric / Threshold |
| :--- | :---: | :---: | :---: | :--- |
| **1. Cyclomatic Complexity** | 20% | `[1-5]` | `[X.X]` | Max `CC <= 10`, nesting `<= 3` |
| **2. DRY & Duplication** | 15% | `[1-5]` | `[X.X]` | Zero duplicated domain/validation logic |
| **3. SOLID Principles** | 25% | `[1-5]` | `[X.X]` | SRP, OCP, LSP, ISP, DIP invariants |
| **4. Anti-Patterns & Smells** | 15% | `[1-5]` | `[X.X]` | Zero God classes, Feature Envy, leaky layers |
| **5. Maintainability** | 10% | `[1-5]` | `[X.X]` | Functions `<= 30-40` LOC, clear English names |
| **6. Interface Robustness** | 15% | `[1-5]` | `[X.X]` | Strict typing, zero swallowed exceptions |
| **Total** | **100%** | — | **`[XX.X]/30`** | `PASSED >= 85%` \| `CONDITIONAL 70-84%` \| `REJECTED < 70%` |

## 2. Actionable Defects (Omit table & write `None.` on clean `PASSED`)

| Priority | Dimension | File & Line | Defect Summary | Required Remediation |
| :---: | :---: | :--- | :--- | :--- |
| `P0` | SOLID / SRP | `src/services/billing.py:120` | God method mixing DB, PDF, and email | Split into `PdfRenderer` and `InvoiceMailer` |
| `P1` | Complexity | `src/utils/parser.py:55` | `CC = 13`, nesting depth `4` | Flatten branches using guard clauses |
