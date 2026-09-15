# Software Testing Best Practices Reference

This language-agnostic reference outlines principles for test automation, structure, mocking, and test case design.

---

## 1. The Testing Pyramid
Maintain a balanced test suite to optimize execution speed and maintenance costs:
* **Unit Tests (70%)**: Test isolated functions, methods, or classes. Fast and hermetic.
* **Integration Tests (20%)**: Test the interaction between modules, databases, or API contracts.
* **End-to-End (E2E) Tests (10%)**: Test complete user journeys through the UI or API gateway, using realistic environments.

---

## 2. Test Structuring & Execution

### 2.1 The AAA Pattern (Arrange, Act, Assert)
Write tests in three clear, separate blocks to increase readability:
1. **Arrange**: Set up database records, input data, and mocks.
2. **Act**: Execute the function or endpoint under test.
3. **Assert**: Validate outputs, database state changes, and mock behaviors.

```python
# Language-agnostic logic example (Python syntax)
def test_user_creation():
    # 1. Arrange
    email = "test@example.com"
    repository = MockUserRepository()

    # 2. Act
    result = create_user(email, repository)

    # 3. Assert
    assert result.id is not None
    assert result.email == email
```

### 2.2 Hermeticity (Isolation)
Tests must be completely isolated:
- **No Shared State**: Never make tests dependent on the execution order of other tests.
- **Db Rollbacks**: Wrap database tests in transactions that roll back after execution.
- **Mock External APIs**: Never hit active third-party APIs during tests. Mock network boundaries.

---

## 3. Manual Test Case Design
When documenting manual or automated test cases, always use this standard structure:

| Field | Description | Example |
| :--- | :--- | :--- |
| **Test ID** | Unique alphanumeric identifier. | TC_AUTH_01 |
| **Title** | Bounded action being verified. | Verify login fails with incorrect password |
| **Prerequisites** | Setup state before running steps. | User registration completed for "user@test.com" |
| **Steps** | Ordered action list to run. | 1. Navigate to `/login`<br>2. Fill email with "user@test.com"<br>3. Fill password with "wrongpass"<br>4. Click login button |
| **Expected Result**| Outcome validation details. | Error banner displayed: "Invalid email or password" |
