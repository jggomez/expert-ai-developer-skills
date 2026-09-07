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

## 3. Delegation & Tools
- **Antigravity Subagent**: Delegate to `flutter-release-engineer` (for Flutter) or `pull-request-expert` / `commit-expert`.
- **Primary Skills**: `commit-expert`, `pull-request-expert`, `flutter-release-engineering`.

## 4. Quality Gate Checklist
- [ ] Full test suite and lint checks pass cleanly.
- [ ] Conventional Commit message verified and staged properly.
- [ ] Pull Request description contains verification commands and release notes.
- [ ] Explicit user confirmation received before production deployment.
