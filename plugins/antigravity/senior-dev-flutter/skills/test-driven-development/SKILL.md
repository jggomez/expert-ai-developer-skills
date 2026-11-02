---
name: test-driven-development
description: Guides the implementation of software using Red-Green-Refactor testing cycles, ensuring high coverage, robust mocks, and testable system designs. Use this skill when asked to write new features, add testing suites, or verify coverage.
---

# Test-Driven Development (TDD) Skill

## Overview
This skill establishes a disciplined Test-Driven Development (TDD) workflow based on the Red-Green-Refactor cycle. It acts as a Software Quality and TDD Specialist, treating untested code as immediate technical debt. It enforces decoupled, highly testable architectures by defining verification contracts and behavioral specifications before writing any production implementation.

## When to Use
### Trigger Scenarios
- Implementing new features, user stories, domain models, or utility logic.
- Fixing software bugs by writing a reproducing regression test first.
- Refactoring complex systems while preserving exact behavior with a fast safety net.
- Measuring and enforcing test coverage boundaries across a codebase.

### When NOT to Use
- **Browser/UI End-to-End journeys**: Route to `qa-tester`.
- **BDD Gherkin specification authoring**: Route to `testing-expert`.
- **Pre-commit and linting pipelines**: Route to `build-and-ci-gates`.
- **Pure code smell identification without testing**: Route to `code-smells-expert`.

## Process
### Phase 1: Framework Discovery & Baseline Run
1. Detect the project's testing framework (`pytest`, `jest`, `vitest`, `go test`, `flutter test`).
2. Run existing tests to verify that the baseline suite is green before making any edits:
   ```bash
   python3 ./skills/test-driven-development/scripts/verify_tests.py
   ```

### Phase 2: Red-Green-Refactor Loop
For every atomic requirement or behavior:
1. **RED**: Write a focused, failing unit test asserting the expected behavior. Follow the Arrange-Act-Assert (AAA) pattern.
   - Run the test suite and confirm the test fails specifically due to the missing behavior (not due to a syntax error or broken import).
2. **GREEN**: Write the minimal amount of production code required to satisfy the test assertions. Avoid premature abstractions. Confirm the test suite passes.
3. **REFACTOR**: Clean up both production code and test code:
   - Eliminate duplication, improve variable and function naming, extract cohesive helpers, and remove dead code.
   - Run `verify_tests.py` after each micro-refactoring step to confirm everything remains green.

### Phase 3: Hermetic Boundary Mocking
1. **Mock External Boundaries**: Mock network calls, file system I/O, database persistence (in unit tests), and external APIs to keep unit tests sub-millisecond fast and deterministic.
2. **One Assertive Focus**: Keep each unit test focused on a single logical behavior or failure mode.
3. **Clean Teardowns**: Ensure fixtures, mocks, and environment variables are cleaned up automatically after test execution.

### Phase 4: Cross-Language Testing Patterns

#### 1. Python (`pytest`) Patterns
- **Fixtures & Scope**: Use explicit fixtures with dependency injection instead of global state or setup/teardown boilerplate:
  ```python
  @pytest.fixture
  def auth_client(db_session):
      client = TestClient(app)
      client.headers = {"Authorization": "Bearer test-token"}
      yield client
  ```
- **Parametrization**: Test boundary conditions and edge cases concisely with `@pytest.mark.parametrize`:
  ```python
  @pytest.mark.parametrize("input_val, expected", [
      ("", False), ("user@example.com", True), ("invalid", False)
  ])
  def test_email_validation(input_val, expected):
      assert validate_email(input_val) is expected
  ```
- **Hermetic Monkeypatching & Spies**: Use `monkeypatch` or `unittest.mock.patch` for external APIs.

#### 2. Dart & Flutter (`testWidgets`) Patterns
- **Widget Testing Lifecycle**: Use `testWidgets` with explicit asynchronous settlement:
  ```dart
  testWidgets('renders login button and handles submit', (WidgetTester tester) async {
    // Arrange
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    // Act
    await tester.enterText(find.byKey(const Key('email_field')), 'dev@example.com');
    await tester.tap(find.byType(ElevatedButton));
    await tester.pumpAndSettle();

    // Assert
    expect(find.text('Dashboard'), findsOneWidget);
  });
  ```
- **Settlement Guard**: Always call `await tester.pumpAndSettle()` after tapping or animating widgets to drain the microtask queue before asserting state.

#### 3. Dataform & BigQuery Assertions
- **Declarative Row-Level Assertions**: In Dataform SQLX pipelines, embed automated validation assertions:
  ```sql
  config {
    type: "assertion"
  }

  SELECT
    order_id,
    COUNT(*) as duplicate_count
  FROM
    ${ref("stg_orders")}
  GROUP BY
    order_id
  HAVING
    duplicate_count > 1
  ```
- **Built-in Quality Assertions**: Enforce uniqueness and nullability constraints in table definitions:
  ```sql
  config {
    type: "table",
    assertions: {
      uniqueKey: ["user_id"],
      nonNull: ["user_id", "email", "created_at"]
    }
  }
  ```

## Usage
### Commands & Automation Scripts
```bash
# Run automated test verification and coverage scanner
python3 ./skills/test-driven-development/scripts/verify_tests.py
```

### Example Prompts
- *"Implement the discount calculation service using strict TDD — write the failing unit test first."*
- *"Write a regression test reproducing the expired token bug, then implement the fix following Red-Green-Refactor."*
- *"Add comprehensive Flutter widget tests with testWidgets and tester.pumpAndSettle() for the checkout screen."*
- *"Create a Dataform assertion verifying uniqueness and non-null constraints for the staging table."*

### Host Execution Instructions
- **Claude Code**: Execute `verify_tests.py` or the project's native test runner via shell commands between TDD phases.
- **Antigravity**: Maintain a tight Red-Green-Refactor loop, verifying test suite execution before reporting completion.

## Red Flags
- Writing production code before writing the failing test.
- Writing assertions that never failed in the RED phase (testing the wrong condition).
- Writing tests that assert implementation details (e.g. private helper calls) rather than public behavioral contracts.
- Flaky tests dependent on real network connections, time of day, or test execution ordering.
- Skipping assertions or using dummy `assert True`.
- Missing `await tester.pumpAndSettle()` in Flutter widget tests leading to unhandled timers or assertions on intermediate frames.

## Verification
- [ ] Failing test written and proven to fail for the expected reason in the RED phase.
- [ ] 100% of unit tests pass cleanly in the GREEN phase.
- [ ] Refactoring completed with zero test regressions.
- [ ] All external I/O boundaries properly isolated and mocked.
- [ ] Cross-language patterns adhere to conventions (`pytest` fixtures, `testWidgets` + `pumpAndSettle()`, Dataform assertions).
- [ ] Automated verification script executes cleanly:
  ```bash
  python3 ./skills/test-driven-development/scripts/verify_tests.py
  ```

## References
For concrete AAA templates, mocking recipes, and test layout guidelines:
- [TDD & Testing Patterns Reference](references/testing-patterns.md)
