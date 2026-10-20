# Docs and Quality Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-docs--and--quality-green?style=flat-square)](.)

The `docs-and-quality` plugin packages documentation standards, testing methodologies, and Andrej Karpathy behavioral guidelines for **Claude Code**. It includes deterministic lifecycle stop gates to enforce anti-lazy code policies (blocking placeholder stubs).

---

## 1. Directory Tree & Architecture

```
plugins/claude/docs-and-quality/
├── README.md                       # This usage manual
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── hooks.json                      # Hook registrations
├── hooks/
│   └── anti-lazy-code-gate.js      # Stop hook blocking TODO stubs & placeholders
└── skills/
    ├── documentation-expert/       # Diátaxis framework & Mermaid diagram standards
    ├── testing-expert/             # AAA pattern, hermetic tests, Gherkin/BDD syntax
    └── guidelines-karpathy/        # Behavioral checklist to avoid over-engineering & LLM pitfalls
```

---

## 2. Bundled Skills (3 Packaged Modules)

1. **`documentation-expert`**: Diátaxis documentation hierarchy, Mermaid.js diagram guides, and `validate_docs.py`.
2. **`testing-expert`**: Arrange-Act-Assert pattern, hermetic test boundaries, Gherkin BDD syntax, and `validate_gherkin.py`.
3. **`guidelines-karpathy`**: Behavioral checklist to keep changes surgical, avoid speculative abstractions, prevent common LLM coding pitfalls, and enforce anti-lazy code standards.

---

## 3. Lifecycle Hooks & Deterministic Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`Stop`** | `hooks/anti-lazy-code-gate.js` | Inspects git diffs before session termination. Scans for lazy placeholders (`TODO: implement later`, `# ... rest of code`, `pass # placeholder`, `/* unimplemented */`). Blocks exit (exit code 2) if stubs are detected. |

---

## 4. Installation

In Claude Code, install from marketplace or local path:
```bash
/plugin install docs-and-quality
# or local:
claude plugin install plugins/claude/docs-and-quality
```
