# Python Core Best Practices & Production Patterns Reference

This catalog details production-ready patterns, modern Python 3.10+ language capabilities, algorithmic performance optimizations, and async concurrency design standards.

---

## 1. Modern Type Safety & Architecture (Python 3.10+)

### 1.1 PEP 604 Union Syntax & Native Generics
- Use built-in generic collections (`list`, `dict`, `set`, `tuple`) instead of importing from `typing`.
- Use union operator `|` for optional and union types instead of `Union` or `Optional`.

```python
# AVOID (Legacy pre-3.10 typing)
from typing import List, Dict, Optional, Union

def process_users(users: List[Dict[str, Union[int, str]]], filter_id: Optional[int] = None) -> List[str]:
    ...

# PREFER (Modern Python 3.10+)
def process_users(users: list[dict[str, int | str]], filter_id: int | None = None) -> list[str]:
    active_users: list[str] = []
    for user in users:
        if filter_id is None or user.get("id") == filter_id:
            active_users.append(str(user.get("name", "")))
    return active_users
```

### 1.2 Structural Typing with `typing.Protocol`
Use `Protocol` to define implicit interfaces (duck typing with type safety) without hard inheritance coupling.

```python
from typing import Protocol

class Renderable(Protocol):
    """Any class implementing render() satisfies this protocol without inheriting."""
    def render(self) -> str: ...

class MarkdownDocument:
    def render(self) -> str:
        return "# Title\nContent"

class HTMLDocument:
    def render(self) -> str:
        return "<h1>Title</h1><p>Content</p>"

def publish(doc: Renderable) -> None:
    print(doc.render())
```

### 1.3 Exception Chaining & Custom Error Hierarchies
Always chain exceptions using `from` to preserve the original traceback cause (PEP 3134). Never swallow exceptions with bare `except:`.

```python
class DatabaseConnectionError(Exception):
    """Raised when the database connection fails."""

def connect_to_storage(db_uri: str) -> None:
    try:
        raw_connect(db_uri)
    except ConnectionRefusedError as err:
        # PREFER: Preserves original stack trace cause
        raise DatabaseConnectionError(f"Failed connecting to {db_uri}") from err
```

### 1.4 Defensive Arguments (No Mutable Defaults)
Never use mutable objects (`list`, `dict`, `set`) as default argument values.

```python
# AVOID (Shared mutable state across all function calls!)
def append_log(message: str, history: list[str] = []) -> list[str]:
    history.append(message)
    return history

# PREFER (Independent allocation per call)
def append_log(message: str, history: list[str] | None = None) -> list[str]:
    if history is None:
        history = []
    history.append(message)
    return history
```

---

## 2. Memory & Speed Optimizations

### 2.1 High-Volume Objects with `@dataclass(slots=True)`
Use `slots=True` (Python 3.10+) on dataclasses to eliminate `__dict__` overhead, reducing memory allocations by 60-80% and speeding up attribute access.

```python
from dataclasses import dataclass

# PREFER: Memory-optimized, immutable value object
@dataclass(slots=True, frozen=True)
class EventRecord:
    event_id: str
    timestamp: float
    payload: str
```

### 2.2 Streaming Pipelines with Generators & `itertools`
Process massive streams or files without materializing full dataset lists in memory.

```python
import itertools

def read_large_log(file_path: str):
    """Generator that yields stripped non-empty lines."""
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()
            if clean_line:
                yield clean_line

# Efficient processing of the first 1,000 log lines without loading the whole file
log_stream = read_large_log("app.log")
first_1000 = list(itertools.islice(log_stream, 1000))
```

### 2.3 Algorithmic Complexity & Collection Selection
- Use `collections.deque` for $O(1)$ pop/append at both ends (never `list.pop(0)` which is $O(N)$).
- Use `set` for lookup checks ($O(1)$ average) instead of `list` ($O(N)$).

```python
from collections import deque

# AVOID: list.pop(0) shifts all N elements in memory (O(N))
queue_list = [1, 2, 3, 4]
first = queue_list.pop(0)

# PREFER: deque.popleft() executes in O(1)
queue_deque = deque([1, 2, 3, 4])
first = queue_deque.popleft()
```

### 2.4 String Building & Memoization
- Use `"".join()` for batch string concatenation instead of repeatedly using `+=` inside loops.
- Use `functools.cache` or `functools.lru_cache` for pure deterministic functions.

```python
from functools import cache

@cache
def expensive_fibonacci(n: int) -> int:
    if n < 2:
        return n
    return expensive_fibonacci(n - 1) + expensive_fibonacci(n - 2)
```

---

## 3. Modern Async & Concurrency (Python 3.11+)

### 3.1 Structured Concurrency with `asyncio.TaskGroup`
Python 3.11 introduced `asyncio.TaskGroup`, which provides safer, structured task lifecycle management compared to `asyncio.gather()`. If any task fails, all remaining tasks are cleanly cancelled.

```python
import asyncio

async def fetch_user(user_id: int) -> dict:
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": f"User_{user_id}"}

async def fetch_all_data(user_ids: list[int]) -> list[dict]:
    results: list[dict] = []
    
    # Structured concurrency: automatically awaits and cancels on error
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_user(uid)) for uid in user_ids]
        
    return [task.result() for task in tasks]
```

### 3.2 Non-Blocking Event Loops (`asyncio.to_thread`)
Never run blocking sync I/O or heavy CPU calculations directly on the async event loop. Use `asyncio.to_thread()` (Python 3.9+) to offload to worker threads.

```python
import asyncio
import time

def sync_heavy_computation(data: str) -> int:
    time.sleep(1) # Simulated sync I/O or CPU work
    return len(data)

async def handle_request(raw_data: str) -> int:
    # PREFER: Offloads blocking work without freezing event loop
    result = await asyncio.to_thread(sync_heavy_computation, raw_data)
    return result
```

---

## 4. Production Logging & Module Export Control

### 4.1 Structured Logging over `print()`
Never use `print()` in library or application code. Always instantiate module-level loggers.

```python
import logging

logger = logging.getLogger(__name__)

def process_transaction(transaction_id: str, amount: float) -> None:
    logger.info("Processing transaction", extra={"transaction_id": transaction_id, "amount": amount})
```

### 4.2 Module Export Boundaries (`__all__`)
Explicitly declare `__all__` in `__init__.py` files to define public module APIs and hide internal helpers.

```python
# __init__.py
__all__ = ["publish", "Renderable"]

from .publisher import publish
from .protocols import Renderable
```
