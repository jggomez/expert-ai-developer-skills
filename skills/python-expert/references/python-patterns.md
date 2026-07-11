# Python Core Best Practices & Performance Optimization

This reference outlines standards for clean code, type safety, performance optimizations, and asynchronous programming in Python.

---

## 1. Clean Code & Type Safety

### 1.1 PEP 8 Compliance & Type Hinting
- Always use descriptive, snake_case names for variables and functions, and CamelCase for classes.
- Implement type hinting on all functions to enable robust static analysis (`mypy`).

```python
from typing import List, Optional

def fetch_active_users(limit: int = 10) -> List[dict]:
    users: List[dict] = []
    # Implementation...
    return users
```

### 1.2 Safe Exception Handling
Never use bare `except:` clauses. Always catch specific exceptions to prevent swallowing system exits or keyboard interrupts.

```python
# AVOID
try:
    process_data()
except:
    pass

# PREFER
try:
    process_data()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except IOError as e:
    logger.error(f"I/O Error: {e}")
```

---

## 2. Memory & Speed Optimizations

### 2.1 Generators for Memory Efficiency
Use generators (`yield`) instead of returning fully materialized lists when processing large datasets, preventing out-of-memory crashes.

```python
# AVOID (Loads entire file into memory)
def read_large_file(file_path: str) -> list:
    with open(file_path, 'r') as f:
        return f.readlines()

# PREFER (Streams line by line)
def read_large_file_generator(file_path: str):
    with open(file_path, 'r') as f:
        for line in f:
            yield line
```

### 2.2 Using `__slots__` for High-Volume Objects
When instantiating millions of small objects, define `__slots__` on the class to restrict dynamic attribute dictionary creation, reducing memory footprint by up to 60-80%.

```python
class LogEntry:
    __slots__ = ['timestamp', 'level', 'message']

    def __init__(self, timestamp: float, level: str, message: str):
        self.timestamp = timestamp
        self.level = level
        self.message = message
```

### 2.3 Optimization of Loops and Lookups
- Use local variables inside loops to avoid repeating global lookups.
- Use `set` lookups (`O(1)`) instead of `list` lookups (`O(N)`).
- Use `join` for string concatenation instead of `+` in loops.

```python
# AVOID
result = ""
for word in list_of_words:
    result += word  # Slow, creates new string in every iteration

# PREFER
result = "".join(list_of_words)  # Fast, allocated in one pass
```

---

## 3. Concurrency & Asyncio

### 3.1 Non-Blocking Event Loops
In asynchronous applications (`asyncio`), never run blocking sync calls (like `time.sleep()`, synchronous DB requests, or heavy computations) directly on the event loop.

```python
import asyncio
import time

# AVOID (Blocks event loop, stopping all incoming requests)
async def process_request():
    time.sleep(2) # Blocking
    return "Done"

# PREFER
async def process_request():
    await asyncio.sleep(2) # Non-blocking yield
    return "Done"
```

### 3.2 Running Blocking Code in Executors
When running CPU-bound calculations or using synchronous database drivers, offload execution to a thread or process pool using the loop executor:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)

def blocking_io_bound_task():
    # Sync database read or file write
    time.sleep(2)
    return "Data"

async def async_endpoint():
    loop = asyncio.get_running_loop()
    # Runs blocking task in separate thread without freezing event loop
    result = await loop.run_in_executor(executor, blocking_io_bound_task)
    return result
```
