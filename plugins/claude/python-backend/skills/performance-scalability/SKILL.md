---
name: performance-scalability
description: Identifies, diagnoses, and remediates performance bottlenecks, memory leaks, and architectural scaling limitations. Use this skill when asked to optimize slow queries, configure caching mechanisms, design asynchronous worker systems, or perform load profiling.
---

# Performance and Scalability Skill

## Overview
This skill identifies, measures, and eliminates performance bottlenecks, memory leaks, and architectural scaling limits. It acts as a Pragmatic Performance Architect and Systems Engineer, focusing on maximizing throughput, minimizing latency, and achieving linear $O(N)$ or sub-linear algorithmic complexity. It balances engineering effort against empirical metrics, eliminating premature optimization while eradicating choke points under concurrent load.

## When to Use
### Trigger Scenarios
- Profiling slow function execution paths, API endpoints, or batch jobs.
- Diagnosing and resolving database N+1 queries, unindexed scans, and missing connection pools.
- Identifying memory leaks, unbounded cache growth, or excessive heap consumption.
- Refactoring high-complexity algorithms (e.g. converting $O(N^2)$ loops to $O(N)$ or $O(1)$ lookups).
- Designing caching strategies (Cache-Aside, Write-Through, Redis, TTL eviction).

### When NOT to Use
- **Premature optimization on unmeasured prototypes**: Implement cleanly first using `code-implementer`.
- **Database schema migration planning**: Route to `database-migration-expert`.
- **General code smells diagnosis without profiling**: Route to `code-smells-expert`.
- **Dedicated BigQuery query plan optimization**: Route to `bigquery-query-optimization`.

## Process
### Phase 1: Automated Bottleneck Scanning
Statically scan the codebase to identify nested complexity loops, unbuffered file I/O, or N+1 query signatures:
```bash
python3 ./skills/performance-scalability/scripts/measure_performance.py scan [optional_path_to_scan]
```

### Phase 2: Runtime Execution & Memory Profiling
Measure actual runtime execution duration and peak memory footprint of specific functions:
```bash
python3 ./skills/performance-scalability/scripts/measure_performance.py profile <path_to_script.py> <function_name>
```

### Phase 3: Scalability Architectural Optimization
Apply proven patterns from the scalability reference:
1. **Database Queries**: Eliminate N+1 queries using eager loading (`select_related`, `joinedload`). Ensure query filters match composite indexes. Implement database connection pooling.
2. **Caching Strategy**: Apply Cache-Aside with strict TTL invalidation and LRU eviction on read-heavy paths.
3. **Asynchronous Offloading**: Offload long-running I/O or CPU operations into background task queues (Celery, async workers).
4. **Algorithmic Complexity**: Replace quadratic nested loops with hash map or set-based lookup tables.

## Usage
### Commands & Automation Scripts
```bash
# Scan repository or directory for performance anti-patterns
python3 ./skills/performance-scalability/scripts/measure_performance.py scan src/

# Profile execution time and memory of a function
python3 ./skills/performance-scalability/scripts/measure_performance.py profile src/data_loader.py process_batch
```

### Example Prompts
- *"Profile this batch data processing function and identify where memory is leaking."*
- *"Scan our backend repositories for N+1 database queries and nested loop bottlenecks."*
- *"Design a Redis caching architecture with Cache-Aside pattern for our product catalog."*

### Host Execution Instructions
- **Claude Code**: Execute `measure_performance.py` in the shell and evaluate profiling telemetry.
- **Antigravity**: Run diagnostic performance scans and benchmark code before and after optimizations.

## Red Flags
- Optimizing code without empirical baseline profiling or benchmark evidence.
- Executing database queries or network requests inside loops (N+1 anti-pattern).
- Storing unbounded data in global in-memory dictionaries without size limits or TTL eviction.
- Blocking the asynchronous event loop with synchronous I/O or heavy computations.
- Sacrificing code readability for negligible sub-microsecond gains.

## Verification
- [ ] Automated bottleneck scan executes and issues resolved:
  ```bash
  python3 ./skills/performance-scalability/scripts/measure_performance.py scan .
  ```
- [ ] Empirical profiling proves latency or memory reduction.
- [ ] No N+1 database queries detected in data-access layers.
- [ ] In-memory caches include explicit TTL or LRU maxsize eviction policies.

## References
For architectural patterns, caching blueprints, and algorithmic recipes:
- [Scalability Patterns Reference](references/scalability-patterns.md)

