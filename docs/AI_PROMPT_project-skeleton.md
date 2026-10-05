# AI Development Prompt — project-skeleton

**Branch:** `feature/project-skeleton`
**Base:** `develop`

Read `CLAUDE.md` and `docs/DEVPLAN.md` → Feature: project-skeleton, which is the contract. Do NOT push; the host workflow handles push and PR.

## What to build

The files in the DEVPLAN feature table. Specifics:

- **`pyproject.toml`** (edit the existing file, keep its `[tool.ruff]` / `[tool.ruff.lint]` sections as they are):
  - `[project]`: name `pogo-triage`, version `0.1.0`, `requires-python = ">=3.11"`, a one-line description, runtime deps `click`, `httpx`, `jinja2`.
  - `[project.optional-dependencies] dev = ["pytest", "ruff==0.16.4", "yamllint"]`.
  - `[project.scripts] pogo-triage = "pogo_triage.cli:main"`.
  - Keep the setuptools `src/` layout (`[tool.setuptools.packages.find] where = ["src"]`).
- **`src/pogo_triage/__init__.py`:** `__version__` read with `importlib.metadata.version("pogo-triage")`.
- **`src/pogo_triage/cli.py`:** a Click group `main` with a `version` command that prints `__version__`. `main()` sets up `logging` (level from `--verbose` flag, default WARNING). No `print` for diagnostics.
- **`tests/test_cli.py`:**
  - `CliRunner`: `--help` exits 0 and lists `version`; `version` exits 0 and prints the version from package metadata.
  - **Installed entry point, for real:** a test that runs the `pogo-triage` console script via `subprocess.run` (find it with `shutil.which`, or next to `sys.executable` in the venv's `bin/`) and asserts `--help` exits 0 and contains `version`, and `version` prints the metadata version. Do not mock this; it proves the package installs.
- **`.github/workflows/ci.yml`** — **replace** the scaffolded file entirely:
  - Triggers: `push` to `main`, `develop`, `feature/**`, `fix/**`, `docs/**`, `chore/**`; `pull_request` to `main`, `develop`; `workflow_dispatch`. **Never** `pull_request_target`. `permissions: contents: read`. No secrets anywhere.
  - Job `lint-and-test` (Python 3.12): `pip install -e '.[dev]'`, then `ruff check .`, `ruff format --check .`, `yamllint .github/`, `pytest -q`. No `|| true`; every step gates.
  - Job `security-scan`: keep the existing gitleaks + pip-audit job from the scaffolded file as-is.
  - Job `ci-ok`, last, copied **exactly** in this form (the rulesets require only this check; skipped must fail):

    ```yaml
      ci-ok:
        runs-on: ubuntu-latest
        needs: [lint-and-test, security-scan]
        if: always()
        steps:
          - name: All required jobs succeeded
            env:
              RESULTS: ${{ join(needs.*.result, ' ') }}
            run: |
              echo "job results: ${RESULTS}"
              for r in ${RESULTS}; do
                [[ "${r}" == "success" ]] || { echo "::error::a required job ended '${r}'"; exit 1; }
              done
    ```
  - Drop the `shellcheck` job (no shell scripts remain).
- **`.yamllint.yml`:** extends `default`; line-length max 120; `truthy` allows `on`; `document-start` disabled. `yamllint .github/` must pass.
- **`.gitignore`:** keep the existing entries; add `dist/`, `.cache/`, and `*.csv` with an exception `!tests/fixtures/*.csv`.
- **Remove scaffold leftovers:** delete `scripts/ci.sh` (CI no longer calls it) and the `scripts/` dir if empty. Keep `.ai/`, `.devcontainer/`, `.pre-commit-config.yaml`, `release.yml`.

## Rules

- Run `ruff check . && ruff format --check . && yamllint .github/ && pytest -q` before EVERY commit; all must pass.
- Do NOT push. Do NOT touch files outside this feature's scope.
- Tick only the DEVPLAN criteria you met in `docs/DEVPLAN.md`; leave its Status line unchanged.
- Commit message: `feat: installable package, CLI entry point and gating CI (project-skeleton)`
