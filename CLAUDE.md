# CLAUDE.md -- AI Context for pogo-triage

## Project

- **Stack:** python
- **Container:** all development happens inside a devcontainer

## Commit Conventions

Follow conventional commits strictly:

- `feat:` -- new feature
- `fix:` -- bug fix
- `docs:` -- documentation only
- `chore:` -- maintenance, dependency updates
- `refactor:` -- code restructuring without behavior change
- `test:` -- adding or updating tests
- `ci:` -- CI/CD changes

## Branching (Gitflow)

This project follows **gitflow**. NEVER commit directly to `main` or `develop`.

### Branch types

| Branch | Purpose | Branches from | Merges into |
|--------|---------|---------------|-------------|
| `main` | Production-ready releases (tagged) | -- | -- |
| `develop` | Integration branch for next release | `main` (initial) | `release/*` |
| `feature/*` | New features and non-urgent work | `develop` | `develop` |
| `release/*` | Release prep (bug fixes, docs only) | `develop` | `main` + `develop` |
| `hotfix/*` | Emergency production fixes | `main` | `main` + `develop` |

### Workflow

1. **Feature work:** `git checkout develop && git checkout -b feature/short-description`
2. Work, commit with conventional commits, push.
3. Open a PR from `feature/short-description` → `develop`.
4. **Release prep:** `git checkout develop && git checkout -b release/vX.Y.Z`
5. Only bug fixes and docs in release branches — no new features.
6. When ready: merge `release/vX.Y.Z` → `main`, tag `vX.Y.Z`, merge back → `develop`.
7. **Hotfix:** `git checkout main && git checkout -b hotfix/description`
8. Fix, merge → `main` (tag), merge → `develop`.

### Branch naming

- `feature/add-cli`, `feature/eth-tracker`
- `release/v1.0.0`, `release/v1.1.0`
- `hotfix/fix-crash`, `hotfix/patch-auth`

## Linting & Formatting

**CRITICAL: You MUST run linting and formatting before EVERY commit.** No exceptions.

```bash
ruff check . && ruff format --check .
```

If linting fails, fix ALL issues before committing. Never use `--no-verify` to skip checks.
A commit that fails lint is a broken commit — treat it as a build failure.

## Docker

- Use `docker compose` (space), NOT `docker-compose` (hyphen).
- Containers run with `--cap-drop=ALL` and `--security-opt=no-new-privileges`.

## Secrets

- NEVER commit secrets, credentials, API keys, or tokens.
- Use `.env.example` with placeholder values; real `.env` is gitignored.
- Check `.gitignore` covers `.env*`, `*.pem`, `*.key`.

## Security

- Pre-commit hooks run gitleaks (secret scanning) and semgrep (static analysis).
- Install hooks: `pre-commit install`
- Run manually: `pre-commit run --all-files`

## Testing

```bash
pytest
```

Run tests before pushing.
