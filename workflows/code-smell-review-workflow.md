# Workflow: Code Smell Auditing & SOLID Refactoring

**Identifier**: `code-smell-review-workflow`  
**Purpose**: Guide developers and agents through static code analysis, detecting Fowler/Beck code smells, assessing SOLID compliance, and applying risk-free refactoring patterns, utilizing Antigravity skills and hooks.

---

## 1. Prerequisites
* Project code compiles and runs successfully.
* Existing test coverage is active and passing (do not refactor code that has no test baseline).

---

## 2. Step-by-Step Workflow

```mermaid
graph TD
    A[Start: Code Ready for Review] --> B[Step 1: Run Static Analysis]
    B --> C[Step 2: Identify Code Smells]
    C -->|God Class / Long Method| D[Step 3: Plan Refactoring Steps]
    D --> E[Step 4: Establish Green Baseline]
    E --> F[Step 5: Apply Surgical Refactoring]
    F --> G[Step 6: Run Regression Tests]
    G -->|Fails| H[Revert Refactoring Step]
    H --> F
    G -->|Passes| I[Step 7: Re-evaluate Complexity]
    I -->|More Smells Exist| D
    I -->|Clean| J[End: Code Smell Quality Gate Passed]
```

### Step 1: Run Static Analysis & Metrics
* **Antigravity Best Practice**: Prioritize running the AST-based smell detector from the local skills catalog instead of writing custom parser scripts:
  ```bash
  # Execute the pre-configured code smells skill detector
  python skills/code-smells-expert/detect_smells.py --path src/
  ```
* Run additional metrics if necessary (e.g. Radon for Cyclomatic Complexity):
  ```bash
  radon cc src/ -a
  ```

### Step 2: Identify Code Smells
Review the code for these specific structural defects:
1. **Large Classes / God Modules**: Any class file with >300 lines or handling unrelated domains.
2. **Long Methods**: Any function exceeding 30-50 lines or containing nested loops/if-conditions deeper than 3 levels (High Cognitive Complexity).
3. **Duplicated Code**: Blocks of identical or highly similar code across modules.
4. **Shotgun Surgery**: Changes in one feature requiring file additions or tweaks across multiple packages.

### Step 3: Plan Refactoring Steps
* Break the refactoring down into tiny, single-focus steps.
* **Workspace Isolation (Optional)**: If testing alternative refactor implementations, spawn an isolated subagent in `branch` or `share` mode using `invoke_subagent` so the main chat session remains clean.

### Step 4: Establish Green Baseline
* Before modifying any line, run the unit test suite covering the target files:
  ```bash
  pytest tests/test_module.py
  ```
* Ensure 100% of tests are passing. *If there are no tests, write unit tests first before refactoring.*

### Step 5: Apply Surgical Refactoring (Karpathy Alignment)
* Execute one single step from your refactoring plan at a time.
* **Extraction Pattern**: Extract methods or classes without changing any variable names or interface contracts. Keep changes minimal.
* **Cleanup Dead Code**: Remove old imports, unused parameters, and redundant helper variables that were replaced.

### Step 6: Run Regression Tests
* Run the test suite immediately after the refactoring step:
  ```bash
  pytest tests/test_module.py
  ```
* If tests fail, immediately revert the changes using `git checkout` or `git restore`, isolate what contract broke, and try again with a smaller step.

### Step 7: Re-evaluate Complexity
* Re-run the AST code smells script (`detect_smells.py`). Confirm that Cyclomatic Complexity score is in the A/B range (Score < 10 per function).

---

## 3. Quality Gate & Verification

Before finalizing the refactor, verify:
- [ ] No changes have been made to the public API contracts or external class interfaces (unless explicitly requested).
- [ ] Linter reports 0 errors and code formatter is applied.
- [ ] 100% of tests pass, confirming 0 behavioral regressions.
- [ ] No comments explaining "obvious" lines are left behind.
