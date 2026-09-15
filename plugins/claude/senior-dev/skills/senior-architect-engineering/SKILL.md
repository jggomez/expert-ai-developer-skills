---
name: senior-architect-engineering
description: Architects, designs, and develops complex software systems using industry best practices and Carnegie Mellon SEI architecture frameworks. Use this skill when needing high-level system design, quality attribute scenarios (NFRs), SEI architectural tactics (Availability, Performance, Security, Modifiability), ATAM trade-off analysis, implementation of patterns (Hexagonal, Clean, Event-Driven, CQRS), or authoring Architectural Decision Records (ADRs).
---

# Senior Architect Engineering Skill

## Overview
This skill guides the design and evaluation of complex software systems using Carnegie Mellon Software Engineering Institute (SEI) architectural frameworks (*Software Architecture in Practice* by Bass, Clements, Kazman). It acts as a Pragmatic Senior Software Architect, translating business drivers into 6-part concrete quality attribute scenarios, selecting proven architectural tactics, conducting Architecture Tradeoff Analysis Method (ATAM) evaluations, and enforcing clean architectural boundaries (Hexagonal Architecture / Ports & Adapters).

## When to Use
### Trigger Scenarios
- Designing high-level software architectures, component topologies, and service boundaries.
- Formalizing non-functional requirements (NFRs) into measurable 6-part SEI quality attribute scenarios.
- Authoring Architectural Decision Records (ADRs) to document technical trade-offs and decisions.
- Applying resiliency and performance tactics (Circuit Breakers, Outbox Pattern, Cache-Aside, Protocols).
- Decoupling core domain logic from frameworks, databases, and third-party APIs.

### When NOT to Use
- **Day-to-day feature implementation**: Route to `code-implementer` or `python-expert`.
- **Initial business requirements gathering**: Route to `product-analyst`.
- **Unit and regression test authoring**: Route to `test-driven-development`.
- **Pre-commit and CI automation**: Route to `build-and-ci-gates`.

## Process
### Phase 1: SEI Quality Attribute Scenarios (NFR Specification)
Define non-functional requirements using SEI's 6-part concrete scenario format:
1. **Source of Stimulus**: Who or what generates the stimulus (e.g., external user, rogue client, network spike).
2. **Stimulus**: The condition arriving at the system (e.g., sudden 10x traffic surge, primary DB failover).
3. **Artifact**: The system subsystem affected (e.g., authentication service, search index).
4. **Environment**: Operational state when stimulus occurs (e.g., normal peak hours, maintenance window).
5. **Response**: How the system responds (e.g., shed non-critical load, failover to read replica).
6. **Response Measure**: Concrete measurable metric (e.g., *p99 latency < 200ms, zero lost transactions*).

### Phase 2: Architectural Tactics & Resiliency
Apply proven architectural tactics across critical quality attributes:
- **Availability**: Circuit Breaker, Active/Passive Redundancy, Graceful Degradation, Heartbeat Monitoring.
- **Performance**: Cache-Aside, Connection Pooling, Asynchronous Task Offloading, Query Optimization.
- **Modifiability**: Dependency Inversion (`typing.Protocol` / interfaces), Ports & Adapters, Separation of Concerns.
- **Security**: Zero Trust validation, Authentication/Authorization at boundaries, Encryption at rest/transit.

### Phase 3: ATAM Trade-off & Sensitivity Analysis
Document the trade-offs for major architectural choices:
- *Trade-off Points*: Competing quality attributes (e.g. distributed caching boosts Performance but complicates Consistency).
- *Sensitivity Points*: Critical parameters influencing behavior (e.g., connection pool sizing).
- *Risks & Non-Risks*: Single points of failure, mitigations, and explicit non-goals.

### Phase 4: Clean Boundaries & Pattern Selection
- **Hexagonal Architecture (Ports & Adapters)**: Keep the Domain Core completely free of framework and database dependencies. Expose Primary (inbound) and Secondary (outbound) ports.
- **Event-Driven Resilience**: Use the Transactional Outbox pattern for atomic state persistence and reliable messaging.
- **KISS & YAGNI**: Default to the simplest architecture that satisfies the quality scenarios; avoid premature distributed microservices.

### Phase 5: Architectural Decision Record (ADR) Generation
Scaffold and record the architectural decision using the automated ADR generator:
```bash
python3 ./skills/senior-architect-engineering/scripts/create_adr.py "<Title>" [Proposed]
```

## Usage
### Commands & Automation Scripts
```bash
# Generate a standardized Architectural Decision Record (ADR)
python3 ./skills/senior-architect-engineering/scripts/create_adr.py "Adopt Hexagonal Architecture for Payment Service"
```

### Example Prompts
- *"Design the architecture for our payment gateway integration using Hexagonal Architecture and author an ADR."*
- *"Evaluate the trade-offs between WebSockets and Server-Sent Events (SSE) for real-time notifications using ATAM."*
- *"Formulate 6-part SEI quality attribute scenarios for our new order processing pipeline."*

### Host Execution Instructions
- **Claude Code**: Execute `create_adr.py` in the workspace shell to generate documentation, then populate architectural sections.
- **Antigravity**: Generate architectural blueprints and ADR files before delegating implementation to coding subagents.

## Red Flags
- Vague, untestable quality attributes ("the API must be fast, secure, and scalable").
- Selecting complex distributed patterns (microservices, Kafka) when a modular monolith satisfies all requirements.
- Making architectural decisions without documenting trade-offs, sensitivity points, and rejected alternatives.
- Coupling core business domain models to database ORM models or web framework decorators.

## Verification
- [ ] Every NFR specified using the 6-part SEI concrete scenario format.
- [ ] ATAM trade-off analysis documents competing quality attributes.
- [ ] Architectural boundaries strictly isolate domain logic from external infrastructure.
- [ ] ADR generated and committed using the automated tool:
  ```bash
  python3 ./skills/senior-architect-engineering/scripts/create_adr.py "<Title>"
  ```

## References
- [SEI Architectural Tactics & ATAM Trade-off Reference](references/sei-architectural-tactics.md)
- [ADR Template Reference](references/adr-template.md)