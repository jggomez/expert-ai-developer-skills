# Test Suite for Agent Skills & Rules

This directory contains the automated test suite for the `skills-programming-ai` repository.

## 📁 Directory Architecture

```text
tests/
├── conftest.py               # Shared pytest fixtures (skill discovery, path resolvers)
├── structure/                # Static & Schema Validation Tests
│   ├── test_skills_structure.py       # YAML frontmatter, name/dir match, broken links, inline script paths, path leaks
│   ├── test_plugin_structure.py       # hooks.json/.mcp.json schema, agents/ frontmatter, root<->plugin skill sync
│   └── test_shared_context_plugin.py  # shared-context plugin layout: dual-host hooks.json, MCP config, host-neutral agent, rules file
├── unit/                     # Unit Tests for Skill Automation Scripts
│   ├── test_skills_scripts.py          # Unit tests for Python/Bash scripts in skills/
│   ├── test_shared_context_scripts.py  # context_snapshot / pack / rollup / list: scaffold, redaction, round-trip, retention
│   ├── test_shared_context_mcp.py      # MCP server tool layer (pure functions, no mcp package needed)
│   └── test_shared_context_hooks.py    # the 3 Node hooks: start prompt, checkpoint nudge, stop flush (both hosts)
├── behavioral/               # Behavioral & LLM Intent Matching Tests
│   └── test_skills_behavioral.py # Skill description trigger coverage & README sync
└── integration/              # End-to-End & Multi-Skill Integration Tests
    └── test_shared_context_handoff.py  # two-agent cross-host handoff, lossless compression, retention, real MCP stdio round-trip
```

## 🚀 Execution Instructions

Run all test suites:
```bash
python3 -m pytest tests/ -v
```

Run a specific test category:
```bash
# Structural tests only
python3 -m pytest tests/structure/ -v

# Unit tests only
python3 -m pytest tests/unit/ -v

# Behavioral tests only
python3 -m pytest tests/behavioral/ -v
```
