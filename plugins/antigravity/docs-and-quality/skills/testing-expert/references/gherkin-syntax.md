# Behavior-Driven Development (BDD) & Gherkin Syntax

Gherkin is a structured, human-readable language used to define system behaviors. It acts as an executable specification across programming languages (e.g. Cucumber, Behave).

---

## 1. Gherkin Keywords & Syntax rules

- **`Feature`**: High-level description of the system capability under test.
- **`Background`**: Defines steps run before *each* scenario in the feature file (ideal for setup steps).
- **`Scenario`**: A single behavior being verified.
- **`Given`**: Puts the system in a known state (Arrange).
- **`When`**: The key action performed by the user or system (Act).
- **`Then`**: The expected outcome or verification (Assert).
- **`And` / `But`**: Links multiple Given, When, or Then steps cleanly.

---

## 2. Gherkin Specification Template

### 2.1 Standard Scenario
```gherkin
Feature: User Login Verification

  Background:
    Given the database contains a registered user with email "user@test.com"

  Scenario: Successful login with correct credentials
    Given the user is on the login page
    When the user enters email "user@test.com" and password "secret123"
    And clicks the login button
    Then the user should be redirected to the dashboard
    And a welcome banner should say "Welcome back!"
```

### 2.2 Scenario Outline (Parameterized Testing)
Use `Scenario Outline` and `Examples` tables to run the same scenario multiple times with different variables:

```gherkin
Scenario Outline: Failed login attempts show validation messages
  Given the user is on the login page
  When the user enters email "<email>" and password "<password>"
  And clicks the login button
  Then the user should see an error message "<error_message>"

  Examples:
    | email          | password    | error_message               |
    | invalid-email  | secret123   | Please enter a valid email  |
    | user@test.com  | wrongpass   | Invalid email or password   |
    |                | secret123   | Email cannot be empty       |
```

---

## 3. Tool Implementations by Language

BDD tools parse Gherkin `.feature` files and execute matching code blocks (Step Definitions):

* **Python**: Use **Behave** or **pytest-bdd**.
  ```python
  @when('the user enters email "{email}" and password "{password}"')
  def step_impl(context, email, password):
      context.page.fill_login(email, password)
  ```
* **JavaScript / TypeScript**: Use **CucumberJS** or **Cypress Cucumber Preprocessor**.
  ```javascript
  When('the user enters email {string} and password {string}', (email, password) => {
      cy.get('#email').type(email);
      cy.get('#password').type(password);
  });
  ```
* **Java**: Use **Cucumber-JVM**.
  ```java
  @When("the user enters email {string} and password {string}")
  public void enterCredentials(String email, String password) {
      loginPage.enterCredentials(email, password);
  }
  ```
