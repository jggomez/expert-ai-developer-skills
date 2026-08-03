---
trigger: model_decision
description: Restrict production builds and deployments, enforce build safety gates, and prevent accidental deployments.
---

# Rule: Deployment Restrictions & Production Safety

**Identifier**: `deployment-restrictions`

## 1. Core Deployment Policy

**NEVER** execute direct deployments to staging or production environments from local terminals or AI agent processes without explicit user confirmation and verified quality gates.

## 2. Protected Deployment Commands

The following commands **MUST** be flagged as protected actions:
* **Firebase**: `firebase deploy`, `npx firebase deploy`
* **Google Cloud**: `gcloud app deploy`, `gcloud run deploy`, `gcloud builds submit`
* **Containers**: `docker push`, `podman push`
* **IaC Infrastructure**: `terraform apply`, `pulumi up`, `npx cdk deploy`
* **Package Registries**: `npm publish`, `twine upload`, `cargo publish`, `poetry publish`

## 3. Mandatory Pre-Deployment Gates

Before proposing any deployment, agents **MUST** execute and pass:
1. **Clean Workspace**: `git status` **MUST** show 0 uncommitted diffs or untracked modifications.
2. **Environment Validation**: Explicitly verify target project/stage flags (`--project`, `--stage`).
3. **Automated Validation**: Run full test suites (`pytest`, `npm test`) and linters with 100% pass rate.
4. **Secret Scanning**: Verify zero hardcoded API keys or credentials exist in deployment packages.
5. **CI/CD Preference**: Trigger production deployments via PR merge/release branch tagging rather than local CLI.
