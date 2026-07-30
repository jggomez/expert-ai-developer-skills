# Test Suite for Agent Skills & Rules

This directory contains the automated test suite for the `skills-programming-ai` repository.

## 📁 Directory Architecture

```text
tests/
├── conftest.py               # Shared pytest fixtures (skill discovery, path resolvers)
├── structure/                # Static & Schema Validation Tests
│   └── test_skills_structure.py  # YAML frontmatter, broken links, path checks
├── unit/                     # Unit Tests for Skill Automation Scripts
│   └── test_skills_scripts.py    # Unit tests for Python/Bash scripts in skills/
├── behavioral/               # Behavioral & LLM Intent Matching Tests
│   └── test_skills_behavioral.py # Skill description trigger coverage & README sync
└── integration/              # End-to-End & Multi-Skill Integration Tests
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
