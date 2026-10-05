# CLAUDE.md -- AI Context for pogo-triage

## What This Is

Pokémon GO collection triage. Reads a Poke Genie CSV export and scores every Pokémon for raids (weighted highest), gym defense and the Great, Ultra and Master PvP leagues. It turns the scores into cost-aware keep/invest/transfer verdicts with one-line reasons and safeguard warnings, builds raid teams for the current boss rotation, and renders one mobile-first, self-contained HTML report.

Public repo, portfolio piece: the README and code quality face outside readers. Single user (the operator). Full spec: `docs/plans/2026-10-05-pogo-triage.md`; feature order: `docs/DEVPLAN.md`.

## Architecture

```
private gist (Poke Genie CSV) ─┐
PvPoke rankings + gamemaster ──┼─> parse ─> score ─> verdicts ─> teams ─> report.html.j2 ─> dist/index.html
ScrapedDuck raids JSON ────────┘   (stdlib csv)  (config/*.toml weights)                    │
                                                                                            v
                      GitHub Actions (workflow_dispatch) ─> wrangler pages deploy ─> Cloudflare Pages behind Access
```

Stateless per run: no database in v1. Compute runs on GitHub Actions; nothing runs on home hardware.

## Project

- **Stack:** Python 3.11+, stdlib `csv` + dataclasses (no pandas), httpx, Click, Jinja2, `logging`, `pathlib`. `src/` layout; CLI entry point `pogo-triage`.
- **Config:** `config/*.toml` (upstream URLs, weights, thresholds, safeguard toggles, Poke Genie column aliases), with env overrides. Never constants in code.
- **Container:** AI development happens in the `.ai/` sandbox (`dtl ai run`).

## Constraints

- **Exports and public JSON only.** No game-account access, automation or unofficial game APIs. No HTML scraping. No write-back or auto-transfer: recommendations only.
- **Real collection data never enters the repo.** Fixtures are synthetic Pokémon only. `*.csv` is gitignored outside `tests/fixtures/`.
- **Public Actions logs.** Default logging emits counts and statuses only, never species, nicknames or IVs. Tests enforce this.
- **Tests never hit the network.** Every network call goes through an injectable httpx client; tests use `httpx.MockTransport`.
- **Deterministic output.** Identical inputs produce byte-identical JSON and HTML. `--today` is injectable wherever dates matter; dates are UTC.
- **One self-contained HTML file.** Inline CSS, no external scripts or stylesheets, Jinja2 autoescape on.
- `logging`, never `print` for diagnostics. `pathlib.Path`, never string paths.

## Security & Trust Boundaries

- **Secrets:** GitHub Actions secrets only (`POGO_GIST_ID`, `POGO_GIST_TOKEN`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`). PR CI never receives secrets and runs on `pull_request`, never `pull_request_target`. Only the dispatch workflow sees them.
- **Least privilege:** workflows use `permissions: contents: read`; the gist token can only read gists; the Cloudflare token can only edit Pages on one account.
- **Untrusted input:** the gist CSV and all upstream JSON are schema-validated, never executed, and autoescaped in HTML.
- **Access:** the report is reachable only through Cloudflare Access (email one-time PIN, one allowed address). The allowlist address lives in the Cloudflare dashboard, never in the repo.

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
