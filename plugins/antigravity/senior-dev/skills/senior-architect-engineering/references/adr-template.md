# ADR-[Number]: [Title]

## Metadata
- **Status**: [Proposed | Accepted | Rejected | Superceded]
- **Date**: [YYYY-MM-DD]
- **Authors**: Antigravity Architect Agent
- **Deciders**: [List of decision makers]

---

## 1. Context & Quality Attribute Requirements
- **Business / Technical Problem**: What challenge or requirement necessitates this architectural decision?
- **Key Quality Attributes (NFRs)**:
  - **Availability**: [e.g. 99.99% uptime, failover MTTR < 30s]
  - **Performance**: [e.g. p99 response time < 100ms under 5,000 req/s]
  - **Modifiability**: [e.g. decoupled payment gateways via Ports & Adapters]

---

## 2. Decision & Architectural Tactics
- **Chosen Solution**: Detailed explanation of the architectural pattern, component layout, and tactics selected.
- **SEI Tactics Applied**:
  - *Fault Recovery*: [e.g. Circuit Breaker + Degradation/Fallback]
  - *Performance*: [e.g. Cache-Aside + Async Worker Pools]
  - *Modifiability*: [e.g. Dependency Inversion via typing.Protocol]

---

## 3. ATAM Trade-off & Sensitivity Analysis
- **Tradeoff Points**:
  - *Security vs Performance*: [e.g. Adding payload encryption increases CPU latency by ~5ms]
  - *Consistency vs Availability*: [e.g. Read-replica caching offers low latency but risks 1s stale reads]
- **Sensitivity Points**:
  - [e.g. Database connection pool max size directly controls system throughput limits]
- **Identified Risks & Mitigation**:
  - *Risk*: Single DB primary node failure.
  - *Mitigation*: Multi-AZ hot standby with automated failover via PgBouncer.

---

## 4. Alternatives Considered
| Alternative | Key Design Characteristics | Rejection Rationale / Drawbacks |
| :--- | :--- | :--- |
| **Alternative A** | Direct synchronous processing | Violates availability under peak surges; causes thread starvation. |
| **Alternative B** | Fully event-sourced architecture | Premature complexity (violates KISS/YAGNI for current scope). |

---

## 5. Consequences & Action Plan
- **Positive Impacts**: [High throughput, linear horizontal scalability]
- **Negative Impacts / Technical Debt**: [Increases operational complexity with Redis cache]
- **Follow-up Tasks**: [Configure Prometheus metrics, set up Circuit Breaker thresholds]
