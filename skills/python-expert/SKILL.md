---
name: python-expert
description: Guides PEP 8 compliance, modern static type hinting (Python 3.10+ PEP 604, Protocols), generator pipelines, memory optimization (slots, dataclasses), structured concurrency (asyncio TaskGroup), and production error handling in Python applications. Use when writing pure Python modules, utility functions, algorithms, or optimizing memory and execution speed.
---

# Python Expert Skill

## Overview
This skill guides the design and implementation of modern, idiomatic (Pythonic), type-safe, and high-performance Python (3.10+) applications. It acts as a Senior Python Core Architect enforcing modern syntax standards (PEP 604 unions, `@dataclass(slots=True)`), zero-copy generator pipelines (`itertools`), structured async concurrency (`asyncio.TaskGroup`), and disciplined defensive error handling.

## When to Use
### Trigger Scenarios
- Writing or refactoring core Python modules, libraries, or backend domain logic.
- Adding strict static type annotations (`mypy`, `pyright`, PEP 604 unions `A | B`, `typing.Protocol`).
- Optimizing memory footprint (e.g., `__slots__`, streaming generators for large datasets).
- Implementing structured asynchronous concurrency or background workers (`asyncio`).
- Diagnosing and refactoring performance bottlenecks and algorithmic complexities.

### When NOT to Use
- **Framework-specific REST API routing**: Combine with `fastapi-expert` for HTTP route serialization.
- **Database schema migrations**: Route to `database-migration-expert`.
- **Pre-commit and CI configuration**: Route to `build-and-ci-gates`.
- **Non-Python language development**: Route to the corresponding language skill.

## Process
### Phase 1: Modern Type Hinting & Interface Design
1. Use built-in generic collections (`list[T]`, `dict[K, V]`, `set[T]`) instead of legacy `typing.List` / `typing.Dict`.
2. Use PEP 604 union syntax `T | None` instead of `Optional[T]`.
3. Define structural interfaces using `typing.Protocol` to enforce duck typing with strict static analysis (`mypy`).

### Phase 2: Memory & Algorithmic Optimization
1. Use `@dataclass(slots=True, frozen=True)` for lightweight, immutable data transfer objects.
2. Stream large datasets with generators (`yield`) and `itertools` pipeline functions (`islice`, `chain`) rather than buffering full lists in RAM.
3. Use `collections.deque` for $O(1)$ append/pop operations on both ends (never `list.pop(0)` which is $O(N)$).
4. Replace linear list searches ($O(N)$) with set or dictionary lookups ($O(1)$).

### Phase 3: Structured Concurrency & Resilience
1. Use `asyncio.TaskGroup()` (Python 3.11+) or scoped task management for concurrent asynchronous tasks.
2. Never execute blocking synchronous I/O or CPU-bound calls directly on the event loop; offload via `asyncio.to_thread()`.
3. Use explicit exception chaining (`raise CustomError(...) from err`) to preserve root cause tracebacks.
4. Never swallow exceptions with bare `except:` or silent `pass`.

### Phase 4: Defensive Coding Invariants
1. **NEVER** use mutable default arguments (`def func(items=[])`). Use `items: list[T] | None = None`.
2. Always manage resources using context managers (`with` / `async with`).
3. Use `logging.getLogger(__name__)` with structured context rather than raw `print()` statements.

## Usage
### CLI Verification Commands
```bash
# Static typing verification
mypy --strict src/

# Linter and formatting check
ruff check src/
ruff format --check src/
```

### Example Prompts
- *"Review this data parsing module to optimize memory usage with slots and generators."*
- *"Refactor our synchronous network clients to use structured asyncio with TaskGroup."*
- *"Add strict mypy-compliant type hints to this package using modern Python 3.10+ syntax."*

### Host Execution Instructions
- **Claude Code**: Execute `mypy` and `ruff` in the workspace shell to verify type safety.
- **Antigravity**: Apply Pythonic guidelines during code generation and run validation checks via workspace tools.

## Red Flags
- Mutable default parameters (`def add_item(target=[])`).
- Bare `except:` catching `BaseException` and masking system exits.
- Running synchronous blocking code (`requests.get`, `time.sleep`) inside async def coroutines.
- Instantiating millions of objects without `__slots__` or `@dataclass(slots=True)`.
- Using `list.pop(0)` in loops causing $O(N^2)$ algorithmic degradation.

## Verification
- [ ] `mypy --strict` passes with zero type errors.
- [ ] No mutable default arguments present in any function signatures.
- [ ] Large dataset iterations use generators or iterators with bounded memory consumption.
- [ ] Async workflows employ `asyncio.TaskGroup` or safe concurrency boundaries without thread blocking.
- [ ] All raised exceptions preserve source context via `from err`.

## References
For detailed code patterns, memory benchmarks, and anti-pattern comparisons:
- [Python Core Best Practices & Performance Optimization](references/python-patterns.md)

