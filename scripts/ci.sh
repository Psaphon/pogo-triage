#!/usr/bin/env bash
# CI lint/format/test script — ONE definition, two callers.
# .github/workflows/ci.yml and dtl's local preflight (_run_lint_and_tests)
# both invoke this script.  Change steps here; CI and local cannot drift
# because there is only one of them.
set -euo pipefail

# Ruff at the pinned fleet version — installed separately from project deps
# so the pin is always honoured even when the project omits ruff from [dev].
pip install -q "ruff==0.16.4"

# Install from the project's declared dependencies — never a hand-written list.
# Detecting the [project.optional-dependencies] section selects the right form.
# A broken extra must fail CI loudly; there is NO || fallback.
if [ -f pyproject.toml ] && grep -qE '^\[project\.optional-dependencies\]' pyproject.toml; then
    pip install -q -e '.[dev]'
elif [ -f requirements.txt ]; then
    pip install -q -r requirements.txt
elif [ -f pyproject.toml ]; then
    pip install -q -e .
fi

ruff check .
ruff format --check .
# Tolerate exit-5 (no tests collected on an empty scaffold); fail on all others.
pytest --tb=short || { rc=$?; [ "$rc" -eq 5 ] && exit 0 || exit "$rc"; }
