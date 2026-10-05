# pogo-triage

A python project scaffolded by dtl.

## Getting Started

Open in VS Code and select **Reopen in Container** when prompted,
or start manually:

```bash
cd .devcontainer
docker compose up -d
```

## Development

All development happens inside the devcontainer. See `CLAUDE.md`
for commit conventions and workflow rules.

## Branch Protection

In GitHub repository settings, require the `ci-ok` status check
(rather than individual matrix job names) so that all CI jobs must
pass before a pull request can merge.

## Security Scanning

CI runs two security checks on every push:

- **Secret scanning** (gitleaks): detects committed credentials and API keys.
- **Dependency audit** (pip-audit / npm audit): flags packages with known CVEs.

### Triaging findings

**Gitleaks** — if a secret is flagged:
1. Rotate the credential immediately (treat it as compromised).
2. Remove it from git history (`git filter-repo` or BFG Repo Cleaner).
3. If the match is a false positive, add a `.gitleaksignore` entry.

**Dependency audit** — if a vulnerable package is flagged:
1. Check the advisory for severity and whether your usage is affected.
2. Update to a patched version (`pip install -U <pkg>` / `npm update <pkg>`).
3. If no fix exists, assess workarounds or document the accepted risk.
