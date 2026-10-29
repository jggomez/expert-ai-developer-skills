# ADR-[Number]: [Title]

> **Status**: [Status] (`Proposed | Accepted | Superseded`) — **Date**: [YYYY-MM-DD]

## 1. Context
<2–5 lines describing the concrete engineering problem, technical/operational constraints, and measurable SLAs (e.g., p99 latency, throughput, consistency, security) forcing a structural choice.>

## 2. Options Considered
1. **Option A — <Name>**: <1–2 lines summarizing approach and main limitation.>
2. **Option B — <Name>**: <1–2 lines summarizing approach and main limitation.>
3. **Option C — <Name> *(Selected)***: <1–2 lines summarizing approach and why it fits constraints.>

## 3. Decision & Justification
Adopt **Option C (<Name>)**. <2–4 lines explaining the exact contract/schema/pattern chosen, dependency boundaries (SOLID / Ports & Adapters where justified), and why it outperforms the rejected options under KISS/YAGNI.>

## 4. Trade-offs
- **+ Benefits**:
  - <Concrete gain in simplicity, latency, reliability, or testability>
- **- Costs & Operational Risks**:
  - <Added constraint, migration cost, or failure mode> -> **Mitigation**: <Concrete safeguard, timeout, or fallback>
