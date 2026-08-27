# Docs and Quality Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-docs--and--quality-green?style=flat-square)](file:///./)

The `docs-and-quality` plugin packages the repository's stack-agnostic documentation and testing standards as a minimal Claude Code plugin: no hooks, no MCP servers, no agents — just three skills that already exist in the root `/skills` catalog, with nothing added.

**Claude Code only** — no Antigravity equivalent exists in this repo for this plugin (see root README §12.2 for why). The three bundled skills themselves are platform-neutral, though — see below.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing any of these three skills under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/docs-and-quality/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor
└── skills/
    ├── documentation-expert/       # Diátaxis framework & Mermaid diagram standards
    ├── testing-expert/             # AAA pattern, hermetic tests, Gherkin/BDD syntax
    └── guidelines-karpathy/        # Behavioral checklist to avoid over-engineering & LLM pitfalls
```

None of these three skills reference Python, a specific framework, or a specific host's tool names — they apply to any language and either Antigravity or Claude Code.

---

## 2. Bundled Skills (3 Packaged Modules)

1. **`documentation-expert`**: Diátaxis documentation hierarchy, Mermaid.js diagram guides, and a `validate_docs.py` link/path checker.
2. **`testing-expert`**: Arrange-Act-Assert pattern, hermetic test boundaries, Gherkin BDD syntax, and a `validate_gherkin.py` syntax checker.
3. **`guidelines-karpathy`**: Behavioral checklist to keep changes surgical, avoid speculative abstractions, and prevent common LLM coding pitfalls.

---

## 3. Example Prompts

- "Write a README for this service following the Diátaxis framework, with a Mermaid diagram of the architecture." (`documentation-expert`)
- "Check this documentation for broken relative links and absolute path leaks." (`documentation-expert`)
- "Write Gherkin BDD scenarios for the password-reset flow, covering the happy path and expired-token case." (`testing-expert`)
- "Review these tests for hermeticity — are any of them hitting a real network call?" (`testing-expert`)
- "Before we add this abstraction, check it against the Karpathy guidelines — do we actually need it yet?" (`guidelines-karpathy`)

---

## 4. Installation

```bash
cp -r ./plugins/docs-and-quality ~/.claude/plugins/docs-and-quality
```
