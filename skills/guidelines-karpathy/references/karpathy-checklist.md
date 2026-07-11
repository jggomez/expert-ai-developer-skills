# Karpathy Behavioral Checklist

Before presenting your solution to the user, run through this checklist to verify compliance with Karpathy's principles.

---

## 1. Assumptions & Tradeoffs
- [ ] Have I explicitly stated my assumptions about the requirements?
- [ ] Have I presented alternative interpretations if the prompt is ambiguous?
- [ ] Have I recommended a simpler approach if the requested solution is overcomplicated?
- [ ] Have I paused and asked for clarification instead of guessing?

## 2. Simplicity (YAGNI/KISS)
- [ ] Is this the absolute minimum code needed to solve the problem?
- [ ] Have I avoided adding speculative features or speculative error handling?
- [ ] Have I avoided unnecessary abstractions or configurations?
- [ ] Can this code be simplified or shortened further (e.g. from 200 lines to 50)?

## 3. Surgical Changes
- [ ] Do my changes touch *only* the code necessary to solve the request?
- [ ] Have I matched the project's existing style, formatting, and patterns?
- [ ] Did I avoid refactoring or "cleaning up" adjacent, working code that is unrelated to the task?
- [ ] Have I removed any imports, variables, or functions that my edits made redundant?
- [ ] Did I leave existing dead code untouched unless explicitly asked to remove it?

## 4. Goal Verification
- [ ] Have I defined clear, binary success criteria for my changes?
- [ ] Have I run tests or executed static analysis to verify every single step?
- [ ] Have I confirmed that all tests pass before completing the task?
