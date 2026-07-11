# FastAPI Design Patterns Reference

This reference outlines standards for routing, request validation, dependency injection, and performance optimizations.

---

## 1. FastAPI Architecture Guidelines

### 1.1 Dependency Injection for DB Sessions
Always use `Depends` to manage SQLAlchemy or Tortoise ORM sessions, ensuring connections are safely closed after request termination.

```python
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from app.db import SessionLocal

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/{item_id}")
def read_item(item_id: int, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.id == item_id).first()
```

### 1.2 Validation with Pydantic v2
- Use Pydantic models for request bodies and response serialization.
- Set `from_attributes = True` inside `Config` (Pydantic v2) to serialize ORM entities.
- Never output DB objects directly; always define a `response_model` to sanitize outputs (preventing password or token leakage).

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True # Maps ORM properties automatically
```

---

## 2. Background Tasks & Middleware

### 2.1 Native FastAPI Background Tasks
Use `BackgroundTasks` for non-blocking operations like sending emails or webhooks directly after a response is returned.

```python
from fastapi import BackgroundTasks

def send_notification(email: str):
    # Long running process
    pass

@app.post("/register")
def register_user(user: UserCreate, background_tasks: BackgroundTasks):
    # Save user...
    background_tasks.add_task(send_notification, user.email)
    return {"status": "User created successfully"}
```
