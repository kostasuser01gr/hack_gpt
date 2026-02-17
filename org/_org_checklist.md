# Org-Wide Security & Quality Checklist

Use this checklist when onboarding a new repository into the security pipeline.

## Per-Repository Setup

- [ ] **Enable GitHub Advanced Security** (Settings → Security → Code security and analysis → GHAS)
- [ ] **Enable Code Scanning (CodeQL)**
  - Try **Default Setup** first: Settings → Security → Code security → Code scanning → CodeQL analysis → Default
  - If Default Setup is unavailable, copy `.github/workflows/codeql.yml` from this repo
  - Adjust the `matrix.language` list for the repo's languages
- [ ] **Verify Copilot Autofix** is enabled (Settings → Code security → Code scanning → Copilot Autofix → Enable)
- [ ] **Add Branch Protection rules**
  - Settings → Branches → Add rule → Branch name pattern: `main`
  - [x] Require status checks to pass: `code-scanning`, `build-and-test`
  - [x] Require branches to be up to date
  - [x] Enforce for administrators
- [ ] **Run initial scan** — push a commit or open a dummy PR to trigger the first CodeQL run
- [ ] **Review initial alerts** under Security → Code scanning alerts

## Using the Reusable Workflow

Instead of copying `codeql.yml` to every repo, use the reusable workflow from the org config repo:

```yaml
# .github/workflows/ci.yml in each repo
name: org-ci
on: [pull_request, push]
jobs:
  security:
    uses: <OWNER>/.github/.github/workflows/reusable-codeql.yml@main
    secrets: inherit
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: npm ci
      - run: npm test --if-present
```

Replace `<OWNER>` with your GitHub org or username.

## Org-Level Setup

- [ ] **Create org config repo**: `<OWNER>/.github`
- [ ] **Place `reusable-codeql.yml`** in `<OWNER>/.github/.github/workflows/reusable-codeql.yml`
- [ ] **Enable GHAS for all repos** (Org Settings → Code security → Enable for all/new repos)
- [ ] **Install Sentry for GitHub Copilot** extension org-wide (GitHub Marketplace → Sentry Copilot)
- [ ] **Install Docker for GitHub Copilot** extension org-wide (GitHub Marketplace → Docker Copilot)
- [ ] **Set org-level branch protection** (Org Settings → Repository → Rulesets)

## Sentry Copilot Extension Setup

1. Install from GitHub Marketplace: [Sentry for GitHub Copilot](https://github.com/marketplace/sentry-copilot)
2. Connect your Sentry project (Settings → Integrations → GitHub → Connect)
3. In VS Code / Codespaces: install `Sentry for Copilot` extension
4. Use prompts like:
   - `@sentry What errors occurred in the last 24 hours?`
   - `@sentry Suggest a fix for issue PROJ-123`
   - `@sentry Generate tests for the fix of commit abc123`

## Docker Copilot Extension Setup

1. Install from GitHub Marketplace: [Docker for GitHub Copilot](https://github.com/marketplace/docker-for-github-copilot)
2. Use prompts like:
   - `@docker Optimize this Dockerfile for production`
   - `@docker Add a healthcheck to my container`
   - `@docker Convert to multi-stage build`
   - `@docker Scan my image for vulnerabilities`

## Branch Protection via CLI

```bash
# Quick setup via GitHub CLI
gh api \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/<OWNER>/<REPO>/branches/main/protection \
  -f required_status_checks[strict]=true \
  -f 'required_status_checks[contexts][]=code-scanning' \
  -f 'required_status_checks[contexts][]=build-and-test' \
  -f enforce_admins=true \
  -f restrictions=null \
  -f required_pull_request_reviews=null
```
