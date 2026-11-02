# Refactoring Techniques Reference

This reference catalog provides standard refactoring techniques grouped by category with concrete before/after code examples.

---

## 1. Composing Methods & Clean API Declarations

### 1.1 Extract Method
- **Definition**: Isolate a cohesive code block with a single purpose into a separate, well-named function.
- **Before**:
  ```python
  def print_details(invoice, outstanding):
      print(f"Customer: {invoice.customer}")
      # print details
      print(f"Outstanding: {outstanding}")
  ```
- **After**:
  ```python
  def print_details(invoice, outstanding):
      print_customer(invoice.customer)
      print_outstanding(outstanding)

  def print_customer(customer):
      print(f"Customer: {customer}")

  def print_outstanding(outstanding):
      print(f"Outstanding: {outstanding}")
  ```

### 1.2 Inline Method
- **Definition**: Replace calls to a simple, self-explanatory method with its actual body to remove redirection noise.
- **Before**:
  ```python
  def get_rating(driver):
      return 2 if more_than_five_late_deliveries(driver) else 1

  def more_than_five_late_deliveries(driver):
      return driver.number_of_late_deliveries > 5
  ```
- **After**:
  ```python
  def get_rating(driver):
      return 2 if driver.number_of_late_deliveries > 5 else 1
  ```

### 1.3 Replace Temp with Query
- **Definition**: Extract a local variable's assignment calculation to a helper method to keep the main method cleaner.
- **Before**:
  ```python
  base_price = quantity * item_price
  if base_price > 1000:
      return base_price * 0.95
  ```
- **After**:
  ```python
  if get_base_price(quantity, item_price) > 1000:
      return get_base_price(quantity, item_price) * 0.95

  def get_base_price(quantity, item_price):
      return quantity * item_price
  ```

---

## 2. Moving Features Between Objects

### 2.1 Move Method / Move Field
- **Definition**: Move a method or field from Class A to Class B if Class B uses or relates to it more than Class A.
- **Before**:
  ```python
  class Account:
      def get_overdraft_charge(self):
          if self.account_type.is_premium:
              # calculation logic using account_type fields
              pass
  ```
- **After**:
  ```python
  class AccountType:
      def get_overdraft_charge(self, days_overdrawn):
          if self.is_premium:
              # logic lives in the AccountType class now
              pass
  ```

### 2.2 Extract Class
- **Definition**: Split a large class with multiple distinct responsibilities into two separate classes.
- **Before**:
  ```python
  class Person:
      def __init__(self):
          self.name = ""
          self.office_area_code = ""
          self.office_number = ""
  ```
- **After**:
  ```python
  class TelephoneNumber:
      def __init__(self, area_code, number):
          self.area_code = area_code
          self.number = number

  class Person:
      def __init__(self, name, telephone):
          self.name = name
          self.telephone = telephone
  ```

### 2.3 Inline Class
- **Definition**: Absorb a class that isn't doing enough back into its host class.
- **Before**:
  ```python
  class Office:
      def __init__(self, code):
          self.code = code

  class Department:
      def __init__(self, office):
          self.office = office
  ```
- **After**:
  ```python
  class Department:
      def __init__(self, office_code):
          self.office_code = office_code
  ```

---

## 3. Organizing Data

### 3.1 Replace Primitive with Object (Value Object)
- **Definition**: Wrap a primitive variable in a class to encapsulate validation, formatting, and operations.
- **Before**:
  ```python
  customer.email = "test@example.com" # raw string, no validation
  ```
- **After**:
  ```python
  class Email:
      def __init__(self, address):
          if "@" not in address:
              raise ValueError("Invalid email")
          self.address = address

  customer.email = Email("test@example.com")
  ```

### 3.2 Introduce Parameter Object
- **Definition**: Group repeating subsets of parameters into a structured object.
- **Before**:
  ```python
  def get_total_sales(start_date, end_date):
      pass
  ```
- **After**:
  ```python
  class DateRange:
      def __init__(self, start, end):
          self.start = start
          self.end = end

  def get_total_sales(date_range):
      pass
  ```

---

## 4. Simplifying Conditional Logic

### 4.1 Replace Nested Conditional with Guard Clauses
- **Definition**: Use early returns/raises (guard clauses) instead of deeply nested if-else structures.
- **Before**:
  ```python
  def get_pay_amount(employee):
      if employee.is_dead:
          result = dead_amount()
      else:
          if employee.is_separated:
              result = separated_amount()
          else:
              result = normal_amount()
      return result
  ```
- **After**:
  ```python
  def get_pay_amount(employee):
      if employee.is_dead:
          return dead_amount()
      if employee.is_separated:
          return separated_amount()
      return normal_amount()
  ```

### 4.2 Replace Conditional with Polymorphism (Strategy/State)
- **Definition**: Move branch behaviors of a type condition into subclasses or strategy objects.
- **Before**:
  ```python
  def get_speed(bird):
      if bird.type == "EUROPEAN":
          return 12.0
      elif bird.type == "AFRICAN":
          return 18.0 - 2.0 * bird.voltage
  ```
- **After**:
  ```python
  class Bird:
      def get_speed(self):
          pass

  class EuropeanBird(Bird):
      def get_speed(self):
          return 12.0

  class AfricanBird(Bird):
      def get_speed(self):
          return 18.0 - 2.0 * self.voltage
  ```

### 4.3 Introduce Special Case (Null Object Pattern)
- **Definition**: Create a subclass or special object representing a "null" or default case to avoid null checks.
- **Before**:
  ```python
  customer_name = "Occupant" if customer is None else customer.name
  ```
- **After**:
  ```python
  class NullCustomer:
      def __init__(self):
          self.name = "Occupant"

  # customer is guaranteed to never be None (NullCustomer instance instead)
  customer_name = customer.name
  ```

---

## 5. Dealing with Inheritance

### 5.1 Pull Up Method / Field & Push Down Method / Field
- **Definition**: Move methods or fields up to a common superclass to eliminate duplication, or down to specific subclasses if only used there.
- **Before**: Both `SavingAccount` and `CheckingAccount` have duplicates of `def calculate_interest()`.
- **After**: Move `calculate_interest` to their common parent `Account` class.

### 5.2 Extract Superclass
- **Definition**: If two classes have similar features, create a superclass and pull the shared features up.
- **Before**:
  ```python
  class Employee:
      def __init__(self, name, rate):
          self.name = name
          self.rate = rate

  class Department:
      def __init__(self, name, manager):
          self.name = name
          self.manager = manager
  ```
- **After**:
  ```python
  class Party:
      def __init__(self, name):
          self.name = name

  class Employee(Party):
      def __init__(self, name, rate):
          super().__init__(name)
          self.rate = rate

  class Department(Party):
      def __init__(self, name, manager):
          super().__init__(name)
          self.manager = manager
  ```

### 5.3 Replace Inheritance with Delegation
- **Definition**: If a subclass uses only a tiny part of the parent class, or is violating Liskov Substitution, make the parent an instance field instead of inheriting.
- **Before**:
  ```python
  class Stack(list): # Stack inherits all list methods, breaking stack contract
      def push(self, val):
          self.append(val)
  ```
- **After**:
  ```python
  class Stack:
      def __init__(self):
          self._storage = list()
          
      def push(self, val):
          self._storage.append(val)
          
      def pop(self):
          return self._storage.pop()
  ```
