# Code Smells Catalog (Fowler/Beck Reference)

This catalog covers all 24 classic code smells from Fowler & Beck's refactoring catalog, classified by category.

---

## 1. Bloaters
Code, methods, and classes that have grown to colossal proportions that are hard to work with.

### 1.1 Long Method
- **Symptom**: A function or method exceeding 30 lines of code.
- **Risk**: Hard to read, understand, debug, and test. High likelihood of duplicate code.
- **Refactoring**: *Extract Method*, *Replace Temp with Query*, *Introduce Parameter Object*, *Preserve Whole Object*, *Replace Method with Method Object*.

### 1.2 Large Class
- **Symptom**: A class containing too many fields, methods, and responsibilities (>300 lines).
- **Risk**: Violates Single Responsibility Principle (SRP). Leads to high coupling and fragility.
- **Refactoring**: *Extract Class*, *Extract Subclass*, *Extract Interface*, *Replace Primitive with Object*.

### 1.3 Long Parameter List
- **Symptom**: A method with more than 3 or 4 parameters.
- **Risk**: Confusing, hard to call, prone to bugs when parameter orders change.
- **Refactoring**: *Introduce Parameter Object*, *Preserve Whole Object*, *Replace Parameter with Query*.

### 1.4 Data Clumps
- **Symptom**: Groups of variables that always appear together in different parts of the code (e.g., street, city, state, zip).
- **Risk**: Missing domain concepts, logic duplication.
- **Refactoring**: *Extract Class*, *Introduce Parameter Object*, *Preserve Whole Object*.

### 1.5 Primitive Obsession
- **Symptom**: Overuse of primitives (integers, strings) instead of simple classes for domain concepts (e.g., zip code, phone number, money, ranges).
- **Risk**: Validation and formatting logic scattered across the codebase instead of encapsulated.
- **Refactoring**: *Replace Primitive with Object*, *Replace Type Code with Subclasses*, *Replace Type Code with State/Strategy*.

---

## 2. Object-Oriented Abusers
Cases where object-oriented principles are ignored, violated, or under-utilized.

### 2.1 Repeated Switches (Switch Statements)
- **Symptom**: Complex `switch` or `if-else` chains checking types or states in multiple places.
- **Risk**: Violates the Open/Closed Principle (OCP). Adding a new type requires modifying all switches.
- **Refactoring**: *Replace Conditional with Polymorphism*, *Replace Type Code with Subclasses*, *Replace Type Code with State/Strategy*.

### 2.2 Temporary Field
- **Symptom**: Fields in an object that are populated only under certain execution paths and otherwise remain null/empty.
- **Risk**: Difficult debugging, high risk of NullPointerExceptions.
- **Refactoring**: *Extract Class*, *Introduce Special Case / Null Object*.

### 2.3 Refused Bequest
- **Symptom**: A subclass inherits methods/fields from a parent but doesn't use them or throws exceptions for them.
- **Risk**: Violates Liskov Substitution Principle (LSP). Indicates a poor inheritance hierarchy.
- **Refactoring**: *Push Down Method/Field*, *Replace Inheritance with Delegation*, *Extract Superclass*.

### 2.4 Alternative Classes with Different Interfaces
- **Symptom**: Two classes perform similar actions but have different method names/signatures.
- **Risk**: Confusing API, duplication, impedes polymorphism.
- **Refactoring**: *Change Function Declaration (Rename)*, *Move Method*, *Extract Superclass*.

---

## 3. Change Preventers
Smells that hinder code modification, requiring modifications in multiple places for a single business logic change.

### 3.1 Divergent Change
- **Symptom**: Having to change many unrelated methods in a single class whenever a specific type of change is made (e.g., editing database schema requires changing serialization, logic, and UI rendering in the same class).
- **Risk**: Violates SRP; class has multiple reasons to change.
- **Refactoring**: *Extract Class*, *Split Phase*.

### 3.2 Shotgun Surgery
- **Symptom**: A single logical change requires making many small modifications across many different classes/files.
- **Risk**: Easy to miss a location, highly coupled code.
- **Refactoring**: *Move Method*, *Move Field*, *Inline Class*.

### 3.3 Parallel Inheritance Hierarchies
- **Symptom**: Creating a subclass for Class A requires also creating a subclass for Class B (e.g., `BillingModel` and `BillingDatabaseConnection`).
- **Risk**: Code size doubles, tight coupling.
- **Refactoring**: *Move Method*, *Move Field* (to merge hierarchies or link them via delegation).

---

## 4. Dispensables
Unnecessary code elements that increase maintenance overhead and cognitive load.

### 4.1 Comments
- **Symptom**: Exorbitant comments explaining *what* a block of code does rather than *why*.
- **Risk**: Comments mask poorly structured or complex code (acting as a "deodorant"). They easily go out of sync.
- **Refactoring**: *Extract Method*, *Rename Variable/Function*, *Introduce Assertion*.

### 4.2 Dead Code
- **Symptom**: Unused variables, methods, parameters, fields, or commented-out code.
- **Risk**: Cognitive clutter, makes navigation difficult.
- **Refactoring**: *Remove/Delete Code*.

### 4.3 Lazy Element (Lazy Class)
- **Symptom**: A class, module, or function that doesn't do enough to justify its existence (often added for "future" use).
- **Risk**: Unnecessary boilerplate and complexity.
- **Refactoring**: *Inline Class*, *Inline Function*, *Collapse Hierarchy*.

### 4.4 Speculative Generality
- **Symptom**: Abstract classes, interfaces, generic parameters, or hooks created "just in case" they are needed later.
- **Risk**: YAGNI violation. Adds unnecessary complexity and hurts readability.
- **Refactoring**: *Collapse Hierarchy*, *Inline Class*, *Remove Parameter*, *Rename Function*.

### 4.5 Data Class
- **Symptom**: A class containing only fields and getters/setters, but no behavior or business logic.
- **Risk**: Encapsulation leak. Other classes manipulate its data, leading to Feature Envy.
- **Refactoring**: *Encapsulate Field*, *Move Method* (move behavior into the data class).

### 4.6 Duplicated Code
- **Symptom**: The same code structure or logic written in multiple places.
- **Risk**: Maintenance nightmare (bug fixes must be repeated).
- **Refactoring**: *Extract Method*, *Pull Up Method*, *Form Template Method*, *Substitute Algorithm*.

---

## 5. Couplers
Excessive or inappropriate coupling between classes.

### 5.1 Feature Envy
- **Symptom**: A method in Class A accesses the data or calls methods of Class B far more than its own class.
- **Risk**: Poor encapsulation; high coupling.
- **Refactoring**: *Move Method*, *Extract Method*.

### 5.2 Inappropriate Intimacy (Insider Trading)
- **Symptom**: Classes that spend too much time reading each other's private/internal fields and behaviors.
- **Risk**: Tightly coupled structure; changes in one class break the other.
- **Refactoring**: *Move Method*, *Move Field*, *Replace Delegation with Inheritance*, *Hide Delegate*.

### 5.3 Message Chains
- **Symptom**: Client calls look like `a.getB().getC().getD().doSomething()`.
- **Risk**: Client is coupled to the entire structural path. Any change along the path breaks the client.
- **Refactoring**: *Hide Delegate*, *Extract Method*, *Move Method*.

### 5.4 Middle Man
- **Symptom**: A class's sole purpose is delegating all calls to another class.
- **Risk**: Over-delegation; redundant class layer.
- **Refactoring**: *Remove Middle Man*, *Inline Class*.

---

## 6. The "Newer" Smells (Fowler 2nd Edition additions)

### 6.1 Mysterious Name
- **Symptom**: Vague, confusing, or misleading names of variables, functions, or classes.
- **Risk**: High cognitive load, misunderstandings leading to bugs.
- **Refactoring**: *Rename Variable*, *Rename Function*, *Rename Field*.

### 6.2 Global Data
- **Symptom**: Global variables, mutable singletons, or shared global state.
- **Risk**: Unpredictable state modifications, extremely hard to test and run concurrently.
- **Refactoring**: *Encapsulate Variable*.

### 6.3 Mutable Data
- **Symptom**: Data that can be modified in place anywhere, especially when shared.
- **Risk**: Side effects, concurrency bugs, hard to trace updates.
- **Refactoring**: *Split Variable*, *Slide Statements*, *Extract Method*, *Replace Derived Variable with Query*.

### 6.4 Loops
- **Symptom**: Complex loops performing filtering, mapping, or accumulation.
- **Risk**: Imperative clutter.
- **Refactoring**: *Replace Loop with Pipeline* (map/filter/reduce style).
