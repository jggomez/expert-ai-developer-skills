# PRD: <feature-name>

## 1. Objective
<2–4 lines stating the concrete user/business problem and measurable outcome this feature delivers.>

## 2. Scope
- **In-Scope**:
  - <Core capability 1>
  - <Core capability 2>
- **Out-of-Scope**:
  - <Explicitly excluded capability or deferred integration>

## 3. User Stories
- **US-01**: **As a** `<role>`, **I want** `<action>`, **so that** `<outcome>`. *(ES: Como `<rol>`, quiero `<acción>`, para `<beneficio>`.)*
- **US-02**: **As a** `<role>`, **I want** `<action>`, **so that** `<outcome>`.

## 4. Acceptance Criteria & Edge Cases
- **AC-01 (`US-01`)**: **Given** `<precondition>`, **when** `<action>`, **then** `<verifiable result>`.
- **AC-02 (`US-01`)**: Reject invalid/missing `<field>` with `<status/error>` before persistence.
- **AC-03 (`US-02`)**: Enforce `<role/permission>` authorization; unauthorized requests return `403`.
- **AC-04 (`US-02` — Edge Case)**: Handle `<empty state / duplicate submission / timeout>` deterministically without partial writes.
