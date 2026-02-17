# Security & Code Scanning

This repository uses **GitHub Code Scanning (CodeQL)** on every pull request and on a weekly schedule (Monday 3:00 AM UTC). Alerts appear under the **Security** tab and as PR annotations.

## How It Works

| Trigger | Description |
|---------|-------------|
| **Pull Request** | CodeQL analyzes JavaScript/TypeScript and Python for vulnerabilities (injection, XSS, path traversal, insecure crypto, etc.) |
| **Weekly schedule** | A scheduled scan catches any issues that may have been missed or newly discovered |
| **Copilot Autofix** | GitHub Copilot may suggest patches for certain alerts directly on the PR |

> **Important:** Always review Copilot Autofix suggestions and run tests before merging. Do not rely solely on automated fixes for high-risk changes.

## Scopes

| Language | Paths |
|----------|-------|
| Python | `*.py`, `ai_engine/`, `cloud/`, `database/`, `exploitation/`, `hackgpt_mcp/`, `performance/`, `reporting/`, `security/` |
| JavaScript/TypeScript | `alpha/`, `HackGPTApp/`, root `.js` files |

## Required Checks

Before merging any PR, the following status checks must pass:
- **code-scanning** (CodeQL analysis)
- **lint** (ruff check + format)
- **test** (pytest suite)
- **security** (bandit + pip-audit)

## Reporting Vulnerabilities

Please see [.github/SECURITY.md](.github/SECURITY.md) for the full vulnerability disclosure policy, response timelines, and contact information.

**Primary Contact:** yashabalam707@gmail.com  
**Subject line:** `[SECURITY] HackGPT Vulnerability Report`
