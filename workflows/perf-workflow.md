# Workflow: Audit Performance (/perf, /webperf)

**Command**: `/perf` (or `/webperf`)  
**Key Principle**: *Measure before you optimize*  
**Identifier**: `perf-workflow`

---

## 1. Objective
Diagnose, benchmark, and remediate runtime performance bottlenecks, frame drops (jank), memory bloat, and database latency using objective telemetry and execution plans.

## 2. Operational Steps
1. **Establish Baseline Telemetry**:
   - Web/Frontend: Lighthouse, Core Web Vitals (LCP, FID/INP, CLS).
   - Flutter: Profile mode frame timing (16ms/60fps budget), DevTools memory snapshot.
   - Database/SQL: Query execution plans (`EXPLAIN ANALYZE`, BigQuery timeline/shuffle).
   - Backend: Profiler flamegraphs, query count (N+1 audit), latency benchmarks.
2. **Isolate Root Bottleneck**:
   - Identify the primary resource bottleneck (CPU bound, I/O bound, lock contention, memory leak).
   - Never apply speculative micro-optimizations without profiling evidence.
3. **Apply Surgical Remediations**:
   - Optimize query indexes, rewrite joins, prune partitions, add caching, or add `RepaintBoundary`.
4. **Re-measure & Benchmark**:
   - Benchmark again under identical conditions to prove improvement.
   - Establish regression guard (e.g. CI frame budget, query cost budget).

## 3. Subagent Delegation & Role Boundaries
- **Role Boundary**: Profiling, query plan inspection, and targeted optimization are delegated to domain specialists.
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="sql-query-optimizer",
        prompt="Profile execution plan and optimize slow queries for: <query-target>"
    )
    ```
    *(For Flutter performance, use `invoke_subagent(name="flutter-implementer", prompt="Profile DevTools timeline and eliminate jank...")`)*
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="sql-query-optimizer",
        prompt="Profile execution plan and optimize slow queries for: <query-target>"
    )
    ```
    *(For Flutter performance, use `Agent(agent="flutter-implementer", prompt="Profile DevTools timeline and eliminate jank...")`)*
- **Primary Skills**: `performance-scalability`, `sql-query-optimization`, `bigquery-query-optimization`, `flutter-performance-profiling`.

## 4. Quality Gate Checklist
- [ ] Baseline telemetry measured before code modification.
- [ ] Root cause identified and isolated.
- [ ] Post-fix benchmark demonstrates objective latency/frame-time improvement.
- [ ] Regression safeguards established.
