---
name: code-smells-expert
description: Analyzes source code to identify, classify, and diagnose architectural design flaws known as "Code Smells" and technical debt. Use this skill when requested to perform a technical audit, evaluate code quality, look for SOLID violations (especially SRP and OCP), or identify reasons why code is difficult to maintain or test. It applies the perspective of a critical Senior Software Architect using standard industry taxonomy (Fowler/Beck).
---

# Code Smells Expert Skill

## Overview
This skill performs structured technical debt audits to identify, classify, and diagnose design flaws known as "Code Smells". It acts as a Senior Software Architect and Technical Debt Diagnostician, grounding assessments in the Fowler/Beck taxonomy. Its primary mission is pure **diagnosis and impact analysis**, explaining *why* structural flaws impede maintainability, extensibility, and testability before any refactoring begins.

## When to Use
### Trigger Scenarios
- Conducting architectural code reviews and technical audits.
- Identifying violations of SOLID principles (especially Single Responsibility and Open/Closed).
- Preparing for refactoring by cataloging structural friction points and antipatterns.
- Explaining why a component is difficult to test, understand, or extend.

### When NOT to Use
- **Applying code changes or executing refactoring**: Route to `refactoring-code-expert`.
- **Security and vulnerability scanning**: Route to `security-audit`.
- **CPU and memory performance profiling**: Route to `performance-scalability`.
- **Writing new unit or integration tests**: Route to `test-driven-development`.

## Process
### Phase 1: Automated Static Analysis
Execute the AST-based smell detection script on specific files or target directories:
```bash
python3 ./skills/code-smells-expert/scripts/detect_smells.py [optional_path_to_file_or_directory]
```
The tool flags threshold violations for method length (>30 lines), class size (>300 lines), parameter count (>4), and nested conditional depth.

### Phase 2: Structural Review via Fowler/Beck Taxonomy
Review classes, methods, and dependencies against the five major smell categories:
1. **Bloaters**: Long Method, Large Class, Primitive Obsession, Long Parameter List, Data Clumps.
2. **Object-Oriented Abusers**: Switch Statements / Type checks violating OCP, Refused Bequest, Alternative Classes with Different Interfaces.
3. **Change Preventers**: Divergent Change (one class modified for multiple unrelated reasons), Shotgun Surgery (single change requires modifying many classes).
4. **Dispensables**: Comments explaining *what* rather than *why*, Duplicate Code, Dead Code, Speculative Generality.
5. **Couplers**: Feature Envy (method accesses another class's data more than its own), Inappropriate Intimacy, Message Chains.

### Phase 3: Diagnostic Report Authoring
For every identified smell, document:
- **Location**: Class/Method, File path, and exact Line numbers.
- **Smell Type**: Precise classification from the catalog.
- **Problem**: Objective violation description (e.g. cyclomatic complexity = 14, parameter count = 6).
- **Risk**: Concrete explanation of how this impedes testing, introduces bugs, or hinders future changes.

## Usage
### Commands & Automation Scripts
```bash
# Scan whole workspace or a specific module
python3 ./skills/code-smells-expert/scripts/detect_smells.py src/
python3 ./skills/code-smells-expert/scripts/detect_smells.py path/to/target_file.py
```

### Example Prompts
- *"Scan our billing service module for code smells and identify which classes violate the Single Responsibility Principle."*
- *"Audit this pull request diff for design anti-patterns, feature envy, and primitive obsession."*
- *"Diagnose why this order processing module is so brittle and propose the cataloged smells that need refactoring."*

### Host Execution Instructions
- **Claude Code**: Run `detect_smells.py` in the shell and summarize findings using the diagnostic reporting format.
- **Antigravity**: Execute `detect_smells.py` via `run_command` and formulate the architectural assessment.

## Red Flags
- Modifying or refactoring code while acting in the diagnosis role (separation of concerns).
- Reporting vague subjective impressions ("this code looks messy") without naming the formal smell.
- Omitting the concrete risk or architectural consequence of the smell.
- Ignoring subtle architectural smells like Feature Envy or Inappropriate Intimacy in favor of only counting lines.

## Verification
- [ ] Static analyzer executed and findings evaluated:
  ```bash
  python3 ./skills/code-smells-expert/scripts/detect_smells.py
  ```
- [ ] All reported smells classified using standard Fowler/Beck taxonomy.
- [ ] File paths and line numbers accurately pinpointed.
- [ ] Concrete business/maintenance risks articulated for each finding.

## References
For full taxonomy definitions, visual examples, and remediation strategies:
- [Smells Catalog Reference](references/smells-catalog.md)