# Workflow: Ship to Production (/ship)

**Command**: `/ship`  
**Key Principle**: *Faster is safer*  
**Identifier**: `ship-workflow`

---

## 1. Objective
Package, verify, commit, and prepare production-ready changes for deployment with small, safe, traceable releases and clean CI/CD validation.

## 2. Operational Steps
1. **Pre-Flight Verification**:
   - Verify working directory status (`git status`).
   - Run full test suite and confirm 100% green.
   - Run linters, formatters, and static security checks.
2. **Semantic Conventional Commit**:
   - Stage relevant files selectively (`git add <files>`).
   - Format commit message matching Conventional Commits (`feat: ...`, `fix: ...`, `refactor: ...`).
3. **Changelog & Versioning**:
   - Update version number if releasing (SemVer).
   - Update release notes / changelog.
4. **Push & Pull Request**:
   - Rebase against target base branch (`git fetch && git rebase origin/main`).
   - Push branch to remote.
   - Author clear PR description using the project template, including test proof and verification instructions.
5. **Production Deployment (When Authorized)**:
   - Verify CI build matrix passes.
   - For Flutter: check native signing and `--dart-define-from-file` flavors.
   - For Backend: verify zero downtime deployment checklist and user consent.

## 3. Subagent Delegation & Role Boundaries
- **Role Boundary**: Release packaging, final compliance audit, and PR formulation are delegated to specialized engineers before shipping.
- **Subagent Delegation across Runners**:
  * **Google Antigravity**:
    ```python
    invoke_subagent(
        name="compliance-verifier",
        prompt="Perform final release gate audit, verify test proof, and confirm zero policy violations for: <branch>"
    )
    ```
    *(For Flutter release packaging, use `invoke_subagent(name="flutter-release-engineer", prompt="Build and package flavor build matrix...")`)*
  * **Anthropic Claude Code**:
    ```python
    Agent(
        agent="compliance-verifier",
        prompt="Perform final release gate audit, verify test proof, and confirm zero policy violations for: <branch>"
    )
    ```
    *(For Flutter release packaging, use `Agent(agent="flutter-release-engineer", prompt="Build and package flavor build matrix...")`)*
- **Primary Skills**: `commit-expert`, `pull-request-expert`, `compliance-verifier`, `flutter-release-engineering`.

## 4. Quality Gate Checklist
- [ ] Full test suite and lint checks pass cleanly.
- [ ] Conventional Commit message verified and staged properly.
- [ ] Pull Request description contains verification commands and release notes.
- [ ] Explicit user confirmation received before production deployment.
