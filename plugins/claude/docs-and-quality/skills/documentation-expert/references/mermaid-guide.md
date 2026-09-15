# Mermaid.js Graphic Reference Guide

Mermaid.js allows you to render diagrams, flowcharts, and sitemaps directly inside markdown using code fences.

---

## 1. Flowcharts (`graph` / `flowchart`)
Flowcharts are ideal for representing execution loops, system pipelines, or branching decisions.

### Flowchart Example
```mermaid
flowchart TD
    Start[User Request] --> Auth{API Authorization}
    Auth -->|Valid Key| Process[Execute Service Route]
    Auth -->|Invalid Key| Reject[Return 401 Unauthorized]
    Process --> End(Response Dispatched)
```

### Syntax Rules
- Specify direction: `TD` (top-down), `LR` (left-right), `BT` (bottom-top).
- Quote node labels containing brackets or parentheses to prevent rendering errors: `Node["Label (Info)"]`.

---

## 2. Sequence Diagrams (`sequenceDiagram`)
Sequence diagrams map class interactions, client-server handshake flows, and chronological events.

### Sequence Example
```mermaid
sequenceDiagram
    actor Client
    participant API as Gateway Controller
    participant DB as Postgres Database

    Client->>API: POST /items (Payload)
    activate API
    API->>DB: INSERT INTO items VALUES (...)
    activate DB
    DB-->>API: Item Record (ID: 105)
    deactivate DB
    API-->>Client: 201 Created (Item JSON)
    deactivate API
```

---

## 3. Entity-Relationship Diagrams (`erDiagram`)
ER diagrams detail database schema models, table relationships, and foreign keys.

### ER Example
```mermaid
erDiagram
    USERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains

    USERS {
        int id PK
        string email
        string password_hash
    }
    ORDERS {
        int id PK
        int user_id FK
        datetime created_at
    }
    ORDER_ITEMS {
        int id PK
        int order_id FK
        int quantity
        decimal price
    }
```
