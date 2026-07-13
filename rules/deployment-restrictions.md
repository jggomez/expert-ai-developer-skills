# Rule: Deployment Restrictions (No Unauthorised Deploys)

**Identifier**: `deployment-restrictions`  
**Purpose**: Protect staging and production environments by restricting deployment commands, enforcing safety gates, and preventing unauthorized or accidental code deployments from developer terminals or AI agent processes.

---

## 1. The Core Policy

**No direct deployment to staging or production environments may be initiated directly from a local terminal session or AI agent process without explicit user authorization and strict security pre-requisites.**

AI agents must treat any command that pushes artifacts, changes infrastructure, or publishes packages as a critical action requiring direct user confirmation and automated pre-checks.

---

## 2. Protected Commands & Target Actions

The following commands are flagged as **protected deployment actions**:

* **Firebase**: `firebase deploy`, `npx firebase deploy`, `firebase deploy --only hosting`
* **Google Cloud**: `gcloud app deploy`, `gcloud run deploy`, `gcloud builds submit`
* **Docker / Container Registries**: `docker push`, `podman push`
* **Infrastructure as Code (IaC)**: `terraform apply`, `pulumi up`, `npx cdk deploy`
* **Package Registries**: `npm publish`, `python -m twine upload`, `cargo publish`, `poetry publish`

---

## 3. Mandatory Pre-Deployment Quality Gates

Before any deployment is proposed or approved, the following checks must be executed:

1. **Clean Workspace Check**: Run `git status` to ensure there are no uncommitted files or local diffs. Deploying untracked modifications is strictly prohibited.
2. **Environment Segregation**: Validate the target environment flags. Ensure you are targeting a development or staging environment before pushing to production. (e.g., check for `--project` or `--stage` arguments).
3. **Linter & Test Execution**: Run the full test suite (`pytest`, `npm test`, etc.) and ensure linting checks (`eslint`, `ruff`) are passing with 0 errors.
4. **Secret Scanning**: Run a regex-based secrets scan on files about to be uploaded (e.g., config files, env setups) to prevent committing private API keys, service account credentials, or certificates.
5. **CI/CD Alignment**: If the project uses a CI/CD pipeline (e.g., GitHub Actions, GitLab CI), prefer triggering deployment by committing code to a release branch or opening a pull request, rather than running manual deploy commands locally.

---

## 4. Execution Sandbox Protocol for Agents

If an agent needs to execute a deployment command:
1. **Explicit Prompting**: The agent must explicitly state the purpose, target environment, and estimated impact of the deployment command to the user.
2. **Review Environment Variables**: Print the target variables (e.g., project ID, staging database URL) to be used so the user can verify them.
3. **Verify IAM / Credentials**: Check permissions before deploying to prevent failed runs due to permission issues (e.g., run `gcloud config list` or check active firebase logins).
4. **Post-Deployment Audit**: Verify that the deployed application is live and run a basic health check on the deployed endpoints to ensure there are no startup crashes or deployment failures.
