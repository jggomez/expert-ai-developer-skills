# Docs and Quality Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-docs--and--quality-green?style=flat-square)](.)

The `docs-and-quality` plugin packages the repository's stack-agnostic documentation standards, testing methodologies, and Andrej Karpathy behavioral guidelines as a self-contained plugin for **Google Antigravity** and **Claude Code**. It includes deterministic lifecycle stop gates to enforce anti-lazy code policies (blocking placeholder stubs).

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing any of these three skills under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/docs-and-quality/
├── README.md                       # This usage manual
├── plugin.json                     # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── hooks.json                      # Hook registrations
├── hooks/
│   └── anti-lazy-code-gate.js      # Stop hook blocking TODO stubs & placeholders
├── rules/
│   └── docs-and-quality-rules.md   # Karpathy guidelines & documentation rules
└── skills/
    ├── documentation-expert/       # Diátaxis framework & Mermaid diagram standards
    ├── testing-expert/             # AAA pattern, hermetic tests, Gherkin/BDD syntax
    └── guidelines-karpathy/        # Behavioral checklist to avoid over-engineering & LLM pitfalls
```

---

## 2. Bundled Skills (3 Packaged Modules)

1. **`documentation-expert`**: Diátaxis documentation hierarchy, Mermaid.js diagram guides, and a `validate_docs.py` link/path checker.
2. **`testing-expert`**: Arrange-Act-Assert pattern, hermetic test boundaries, Gherkin BDD syntax, and a `validate_gherkin.py` syntax checker.
3. **`guidelines-karpathy`**: Behavioral checklist to keep changes surgical, avoid speculative abstractions, prevent common LLM coding pitfalls, and enforce anti-lazy code standards.

---

## 3. Lifecycle Hooks & Deterministic Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`Stop`** | `hooks/anti-lazy-code-gate.js` | Inspects git diffs before session termination. Scans for lazy placeholders (`TODO: implement later`, `# ... rest of code`, `pass # placeholder`, `/* unimplemented */`). Blocks exit if stubs are detected. |

---

## 4. Example Prompts

- "Write a README for this service following the Diátaxis framework, with a Mermaid diagram of the architecture." (`documentation-expert`)
- "Check this documentation for broken relative links and absolute path leaks." (`documentation-expert`)
- "Write Gherkin BDD scenarios for the password-reset flow, covering the happy path and expired-token case." (`testing-expert`)
- "Review these tests for hermeticity — are any of them hitting a real network call?" (`testing-expert`)
- "Before we add this abstraction, check it against the Karpathy guidelines — do we actually need it yet?" (`guidelines-karpathy`)

---

## 5. Installation

**Antigravity CLI**:
```bash
agy plugin install ./plugins/antigravity/docs-and-quality
```

**Claude Code**:
```bash
claude plugin install plugins/claude/docs-and-quality
```
