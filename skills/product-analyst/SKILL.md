---
name: product-analyst
description: Analyzes initial user inquiries, identifies business goals, asks clarifying questions, and constructs structured Product Requirements Documents (PRDs). Use when defining new features, breaking down complex user prompts, or establishing scope boundaries.
---

# Product Analyst Skill

## Overview
This skill guides the analysis of raw user requests into actionable product specifications. It provides a structured framework for requirement discovery, gap analysis, and specification authoring.

## Procedural Workflow

### Phase 1: Context & Gap Analysis
1. Inspect input files or user prompts to identify the core objective.
2. Cross-reference existing system code or specifications using `grep_search` or `view_file` to determine existing patterns.
3. Evaluate the request across four core vectors:
   - **User Intent**: What is the primary user goal?
   - **Scope Boundaries**: What is explicitly included or excluded?
   - **Edge Cases**: What failure modes or alternative paths exist?
   - **Constraints**: Are there hard technical, performance, or business constraints?

### Phase 2: Requirements Clarification
If critical information is missing or ambiguous:
- Formulate precise, option-based questions using `ask_question`.
- Avoid vague questions; present clear tradeoffs (e.g., "Should authentication support OAuth2 only, or username/password as well?").

### Phase 3: Deliverable Generation
Generate the final specification as a structured markdown document following the template below.

---

## Output Template: Product Requirements Document (PRD)

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
- **Security**: Data at rest must be encrypted using AES-256.
- **Scalability**: Support up to 10,000 concurrent active users.

## 6. Acceptance Criteria
- [ ] User can log in with valid credentials.
- [ ] System returns explicit error messages for invalid attempts.