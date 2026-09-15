---
name: product-analyst
description: Analyzes initial user inquiries, identifies business goals, asks clarifying questions, and constructs structured Product Requirements Documents (PRDs). Use when defining new features, breaking down complex user prompts, or establishing scope boundaries.
---

# Product Analyst Skill

## Overview
This skill guides the analysis of raw user requests into actionable product specifications. It acts as a Principal Product Analyst providing a structured framework for requirement discovery, scope boundary delineation, gap analysis, and specification authoring before any architectural or implementation code is written.

## When to Use
### Trigger Scenarios
- Initial phase of new feature development, user stories, or product workflows.
- Analyzing ambiguous, underspecified, or multi-faceted user requests.
- Defining functional requirements (FRs), non-functional requirements (NFRs), and explicit scope boundaries (In-Scope vs. Out-of-Scope).
- Establishing acceptance criteria and edge cases before engineering handover.

### When NOT to Use
- **Architectural pattern selection**: Route to `senior-architect-engineering`.
- **Direct coding or bug fixing**: Route to `code-implementer` or `test-driven-development`.
- **Pure code smells audit**: Route to `code-smells-expert`.
- **Trivial syntax/config edits**: Perform directly without a PRD.

## Process
### Phase 1: Context & Gap Analysis
1. Inspect input prompts or problem statements to uncover the root business problem.
2. Cross-reference existing codebase patterns, data models, or endpoints.
3. Evaluate the request across four core vectors:
   - **User Intent**: What is the primary user goal?
   - **Scope Boundaries**: What is explicitly included or excluded?
   - **Edge Cases**: What failure modes or alternative paths exist?
   - **Constraints**: Are there hard technical, performance, or business constraints?

### Phase 2: Requirements Clarification
If critical information is missing or ambiguous:
- Formulate targeted, option-based clarifying questions with concrete trade-offs.
- Avoid open-ended queries; present concrete technical options (e.g., *"Should authentication support OAuth2 only, or username/password as well?"*).

### Phase 3: Deliverable Generation
Scale the deliverable to the request: a small change needs a concise requirements note (goals, scope, acceptance criteria); new features or system-level modules require a full PRD.

#### Product Requirements Document (PRD) Template
```markdown
# Product Requirements Document (PRD)

## 1. Executive Summary
Brief high-level description of the feature or product vision.

## 2. Business Goals & Objectives
- Objective 1
- Objective 2

## 3. Scope
### In-Scope
- Feature / Capability 1
- Feature / Capability 2
### Out-of-Scope
- Explicitly excluded items

## 4. Functional Requirements (FRs)
| ID | Title | Description | Priority (P0/P1/P2) |
|---|---|---|---|
| FR-01 | User Auth | Allow users to register using email and password. | P0 |
| FR-02 | Profile View | Display user profile information upon login. | P1 |

## 5. Non-Functional Requirements (NFRs)
- **Performance**: Response times < 200ms for standard requests.
- **Security**: Data at rest encrypted using AES-256.
- **Scalability**: Support up to 10,000 concurrent active users.

## 6. Acceptance Criteria
- [ ] User can log in with valid credentials.
- [ ] System returns explicit error messages for invalid attempts.
```

## Usage
### Example Prompts
- *"Analyze this user request for a team workspace invitation flow and generate a PRD with FRs, NFRs, and acceptance criteria."*
- *"We want to add export functionality for reports. Help me define the scope boundaries and identify edge cases."*
- *"Break down this high-level epic into atomic user stories and functional requirements."*

### Host Execution Instructions
- **Claude Code**: Invoke directly at the beginning of a feature prompt to generate the requirements artifact.
- **Antigravity**: Launch as a specialized subagent or initial step before passing output to `senior-architect-engineering` and `code-implementer`.

## Red Flags
- Commencing implementation or architectural design before core requirements and scope boundaries are established.
- Asking open-ended, vague questions that place the cognitive burden back on the user without proposed alternatives.
- Creating an excessively long, bureaucratic PRD for a minor bug fix or trivial change.
- Omission of explicit Out-of-Scope boundaries, causing scope creep during implementation.

## Verification
- [ ] Core business objective and user intent clearly stated.
- [ ] Explicit In-Scope and Out-of-Scope boundaries defined.
- [ ] Functional Requirements assigned unique IDs (`FR-01`, `FR-02`) and priorities (`P0`, `P1`, `P2`).
- [ ] Non-Functional Requirements (NFRs) specified with measurable metrics.
- [ ] Acceptance criteria verifiable and ready for QA test mapping.