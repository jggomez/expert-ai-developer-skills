# SEI Architectural Tactics & ATAM Trade-off Reference

This reference is based on the Carnegie Mellon **Software Engineering Institute (SEI)** architecture framework (*Software Architecture in Practice* by Bass, Clements, and Kazman). It outlines Quality Attribute Scenarios, Architectural Tactics, and the Architecture Tradeoff Analysis Method (ATAM).

---

## 1. SEI Quality Attribute Scenarios (NFR Specification)

Every Quality Attribute (Non-Functional Requirement) **MUST** be specified using SEI's 6-part concrete scenario format rather than vague adjectives (e.g., replace "the system must be fast and secure" with concrete scenarios):

```
┌─────────────────┐       ┌──────────┐       ┌──────────┐
│ 1. Source       ├──────>│ 2.       ├──────>│ 3.       │
│    (User/Client)│       │  Stimulus│       │  Artifact│
└─────────────────┘       └──────────┘       └──────────┘
                                                  │
┌─────────────────┐       ┌──────────┐            ▼
│ 6. Response     │<──────┤ 5.       │<───┌─────────────┐
│    Measure      │       │  Response│    │ 4.          │
│    (p99 < 50ms) │       │  (Process│    │  Environment│
└─────────────────┘       └──────────┘    └─────────────┘
```

| Scenario Element | Description | Concrete Example |
| :--- | :--- | :--- |
| **1. Source** | Entity generating the stimulus. | External API Client / Peak Concurrent Users |
| **2. Stimulus** | Condition requiring response. | 10,000 req/sec surge during flash sale |
| **3. Artifact** | Component under test. | Checkout Order Service & Database |
| **4. Environment** | System operational state. | Normal peak operation / Degraded DB replica |
| **5. Response** | System action taken. | Process orders asynchronously & throttle excess |
| **6. Response Measure** | Quantifiable metric. | Latency p99 < 150ms, zero dropped transactions |

---

## 2. SEI Architectural Tactics Catalog

Architectural Tactics are design decisions that directly influence a Quality Attribute response.

### 2.1 Availability & Fault Tolerance Tactics
* **Fault Detection**:
  - *Ping/Echo & Heartbeat*: Periodically query service endpoints to detect unresponsive nodes.
  - *Sanity Checking*: Validate internal data structures before state commits.
* **Fault Recovery**:
  - *Active Redundancy (Hot Spare)*: All nodes process traffic concurrently; zero failover downtime.
  - *Passive Redundancy (Warm/Cold Spare)*: Primary node processes; secondary syncs state and takes over on failure.
  - *Circuit Breaker*: Intercept repeated external service failures, trip open immediately to prevent cascading thread starvation, and fall back to local cache or default response.
  - *Graceful Degradation*: Disable non-critical features (e.g., recommendations) when system load exceeds capacity.

### 2.2 Performance & Scalability Tactics
* **Control Resource Demand**:
  - *Rate Limiting & Throttling*: Bound incoming client request rates at API Gateways.
  - *Batching*: Combine multiple small operations into a single network or DB payload.
* **Manage Resources**:
  - *Increase Concurrency*: Use async worker pools (`asyncio`, thread/process pools).
  - *Cache-Aside*: Store read-heavy queries in memory (Redis) with explicit TTLs.
  - *Database Connection Pooling*: Reuse pre-allocated connections (`PgBouncer`).
* **Resource Allocation**:
  - *Horizontal Auto-Scaling*: Dynamically scale stateless container instances based on CPU/memory thresholds.

### 2.3 Modifiability & Maintainability Tactics
* **Reduce Coupling**:
  - *Encapsulate*: Hide internal implementation details behind stable interfaces.
  - *Dependency Inversion (DIP)*: Depend on abstractions (`typing.Protocol`), not concrete classes.
  - *Use Intermediary (Adapters/Ports)*: Decouple domain core from external infrastructure (Hexagonal Architecture).
* **Increase Cohesion**:
  - *Single Responsibility (SRP)*: Keep modules focused on a single business capability.

### 2.4 Security Tactics
* **Resist Attacks**:
  - *Authenticate & Authorize*: Verify identity and enforce least-privilege RBAC/ABAC on every endpoint.
  - *Validate Inputs*: Sanitize and validate all external payloads at system boundaries via schemas.
  - *Encrypt Data*: Encrypt data in transit (TLS 1.3) and at rest (AES-256-GCM).
* **Detect & Recover**:
  - *Audit Trails*: Log all security-sensitive operations with immutable, structured logs.

---

## 3. ATAM (Architecture Tradeoff Analysis Method)

When making architectural decisions, perform an explicit ATAM trade-off analysis:

- **Tradeoff Point**: A design decision that affects multiple quality attributes in opposite directions.
  - *Example*: Adding AES-256 payload encryption increases **Security** but degrades **Performance** (increases CPU latency).
  - *Example*: Adding Redis Cache-Aside increases **Performance** but decreases **Consistency** (risk of stale reads).
- **Sensitivity Point**: A design decision for which a small change produces a significant response in a quality attribute.
  - *Example*: Database connection pool max size directly controls **Throughput** and **Availability**.
- **Risk**: A decision that may lead to undesirable consequences.
  - *Example*: Using single-master database replication without automated failover is an **Availability Risk**.

---

## 4. Hexagonal Architecture (Ports & Adapters) Blueprint

```
                      ┌─────────────────────────────────────────┐
                      │             APPLICATION CORE            │
                      │                                         │
 ┌──────────────┐     │   ┌──────────────┐   ┌──────────────┐   │     ┌──────────────┐
 │ Primary      ├────>│──>│ Primary Port │──>│ Domain Use   │   │     │ Secondary    │
 │ Adapter      │     │   │ (Interface)  │   │ Case / Model │   │     │ Adapter      │
 │ (REST / CLI) │     │   └──────────────┘   └──────┬───────┘   │     │ (Postgres DB)│
 └──────────────┘     │                             │           │     └──────▲───────┘
                      │                      ┌──────▼───────┐   │            │
                      │                      │ Secondary    │───│────────────┘
                      │                      │ Port (DB IF) │   │
                      │                      └──────────────┘   │
                      └─────────────────────────────────────────┘
```

- **Domain Core**: Pure business logic with zero framework dependencies.
- **Primary Ports (Inbound)**: Interfaces exposing domain use cases.
- **Secondary Ports (Outbound)**: Interfaces describing required external capabilities (DB repositories, Email senders).
- **Adapters**: Concrete implementations (FastAPI router, SQLAlchemy repository, SendGrid email client).
