# ADR-NNN: <Short Flutter Decision Title>

> **Status**: `Proposed | Accepted | Superseded by ADR-MMM` — **Date**: `YYYY-MM-DD`

## 1. Context
<2–5 lines stating the concrete Flutter engineering problem, state/async/platform constraints, and measurable frame-budget or delivery requirements (`<= 5 lines`).>

## 2. Options Considered
1. **Option A — <Name>**: <1–2 lines summarizing approach (e.g., `setState` / `ValueNotifier`) and main limitation.>
2. **Option B — <Name>**: <1–2 lines summarizing approach (e.g., `flutter_bloc`) and main limitation.>
3. **Option C — <Name> *(Selected)***: <1–2 lines summarizing approach (e.g., `flutter_riverpod`) and why it fits constraints.>

## 3. Decision & Justification
Adopt **Option C (<Name + version>)** across `<scope>`. <2–3 lines defining the UI / Domain / Data boundary, package/folder ownership, and why it wins under KISS/YAGNI.>

## 4. Trade-offs & Reviewer Compliance
- **+ Pros**: <Concrete gain in rebuild isolation, testability, or developer ergonomics.>
- **- Cons**: <Added dependency, codegen step, or migration cost> -> **Mitigation**: <Concrete safeguard.>
- **Reviewer Compliance (`flutter-reviewer`)**: <1-line lint/PR rule, e.g., "Zero `dio` imports outside `lib/src/data/`; no secondary state library outside `legacy/`".>
