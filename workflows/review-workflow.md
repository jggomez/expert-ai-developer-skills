# Workflow: Review Before Merge (/review)

**Command**: `/review`  
**Key Principle**: *Improve code health*  
**Identifier**: `review-workflow`

---

## 1. Objective
Conduct an exhaustive, machine-first code review on diffs and pull requests, classifying findings into concrete blocking defects vs non-blocking suggestions to improve codebase health.

## 2. Operational Steps
1. **Run Automated Baseline First**:
   - Execute linters, tests, and audit scripts before starting manual semantic review.
2. **Inspect Diff Against Checklist**:
   - Check for memory leaks, resource leaks (open streams/controllers missing dispose).
   - Check error handling, edge cases, and unexpected side effects.
   - Check adherence to ADRs and architecture decisions.
3. **Formulate Concrete Findings**:
   - Every raised issue MUST include `file:line` and a concrete failure mechanism.
   - Avoid subjective aesthetic nitpicks; focus on correctness, stability, and maintainability.
4. **Deliver Decisive Verdict**:
   - Categorize into **Blocking** (correctness, security, leak, ADR break) vs **Suggestions**.
   - Provide concrete code remediations for all blocking issues.

## 3. Delegation & Tools
- **Antigravity Subagent**: Delegate to `compliance-verifier` (or `flutter-reviewer`).
- **Primary Skills**: `detect-code-smells`, `flutter-review-checklist`, `pull-request-expert`.

## 4. Quality Gate Checklist
- [ ] Diff reviewed with file:line citations for all issues.
- [ ] ADR conformance verified against `doc/adr/`.
- [ ] Blocking vs non-blocking issues clearly differentiated.
- [ ] Actionable remediations provided for all blocking findings.
