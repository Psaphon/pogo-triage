# Development Plan: pogo-triage

**Status:** In Progress
**Created:** 2026-10-05
**Updated:** 2026-10-05

## Overview

Pokémon GO collection triage. Reads a Poke Genie CSV export, scores every Pokémon for raids, gym defense and the three PvP leagues, turns the scores into cost-aware keep/invest/transfer verdicts with safeguard warnings, builds raid teams for the current boss rotation, and publishes a mobile-first report. Runs on GitHub Actions (manual dispatch) and publishes to Cloudflare Pages behind Cloudflare Access. Source plan: `docs/plans/2026-10-05-pogo-triage.md`.

**Statuses:** `Ready (supervised)` features are built by the PM in session (`project-skeleton` sets up the CI gate; `gist-ingest` and `actions-pipeline` need operator credentials; `docs-readme` waits for `actions-pipeline`). `Held (deps)` features are flipped to `Not Started` by the PM only once their dependencies are `Merged` (the nightly loop ignores `Depends on:`).

## Constraints

- Exports and public JSON only; no game-account interaction and no HTML scraping
- Upstream URLs, weights, thresholds, safeguard toggles and column aliases are config (`config/*.toml`, env overrides), never constants in code
- Real collection data never enters the repo; fixtures are synthetic Pokémon only
- Default logging emits counts and statuses only, never species, nicknames or IVs (Actions logs are public)
- Every network call goes through an injectable httpx client, so tests use `httpx.MockTransport` and never touch the network
- `--today` is injectable wherever dates matter; dates are handled in UTC
- Output is deterministic: identical inputs produce byte-identical JSON and HTML
- `logging` (never `print` for diagnostics), `pathlib.Path`, Click
- The report is one self-contained HTML file: inline CSS, no external scripts or stylesheets

---

## Feature: project-skeleton

**Branch:** `feature/project-skeleton`
**Depends on:** none
**Status:** Merged (#2)
**Requires:** ai

### Goal

An installable package with a CLI entry point and CI that gates PRs on lint and tests.

### Acceptance Criteria

- [x] In a fresh venv, `pip install -e ".[dev]"` exits 0, and the installed `pogo-triage --help` (run via subprocess) exits 0 and lists `version`
- [x] `pogo-triage version` exits 0 and prints the version read from package metadata
- [x] `.github/workflows/ci.yml` runs on every PR to `develop`: installs from `pyproject.toml` (`.[dev]`), then runs `ruff check .`, `ruff format --check .`, `yamllint .github/` and `pytest`
- [x] ruff is pinned to `0.16.4` in the dev extras, with an explicit `select` in `pyproject.toml`
- [x] CI uses no secrets and runs on `pull_request`, never `pull_request_target`
- [x] All tests pass
- [x] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Create | Metadata, deps (click, httpx, jinja2), dev extras (pytest, ruff 0.16.4, yamllint), ruff `select` |
| `src/pogo_triage/__init__.py` | Create | Package init, version |
| `src/pogo_triage/cli.py` | Create | Click group with `version` |
| `tests/test_cli.py` | Create | CliRunner and installed-entry-point subprocess tests |
| `.github/workflows/ci.yml` | Create | PR gate: ruff, yamllint, pytest |
| `.yamllint.yml` | Create | yamllint config |
| `.gitignore` | Create | Python defaults, `dist/`, `.cache/`, `*.csv` outside `tests/fixtures/` |

### Key Decisions

- `src/` layout and extras-based installs: CI installs exactly what `pyproject.toml` declares
- `*.csv` is gitignored outside fixtures, so a real export can't be committed by accident

### Notes

The PM makes the lint and test jobs required checks on `develop` once this merges. Overnight features depend on that gate.

---

## Feature: pokegenie-csv-parser

**Branch:** `feature/pokegenie-csv-parser`
**Depends on:** project-skeleton
**Status:** Merged (#3)
**Requires:** ai

### Goal

Parse a Poke Genie CSV export into typed records, mapping columns by header name.

### Acceptance Criteria

- [ ] `pogo-triage parse tests/fixtures/pokegenie_sample.csv` exits 0 and prints a summary (total, shiny, lucky, shadow, purified, costume, 100% IV). The test asserts the exact counts built into the fixture.
- [ ] A fixture with the same rows in a different column order produces identical records (asserted equal)
- [ ] `pokegenie_malformed.csv`: the command exits 0, logs one warning per bad row naming the row number, and the summary counts only the valid rows
- [ ] An empty file exits 0 with `0 records`; a file missing a required column exits non-zero, and stderr names the column
- [ ] Column aliases are loaded from `config/pokegenie_columns.toml`; adding an alias there (in a temp config) makes a renamed header parse without code changes
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/models.py` | Create | `PokemonRecord` dataclass (species, form, nickname, CP, level, IVs, moves, flags, catch date) |
| `src/pogo_triage/pokegenie.py` | Create | Header-mapped parsing and validation |
| `config/pokegenie_columns.toml` | Create | Canonical field → accepted header names |
| `src/pogo_triage/cli.py` | Modify | Add `parse` command |
| `tests/fixtures/pokegenie_sample.csv` | Create | Synthetic sample covering every flag |
| `tests/fixtures/pokegenie_malformed.csv` | Create | Bad rows (missing IVs, non-numeric CP, blank species) |
| `tests/test_pokegenie.py` | Create | Parser and CLI tests |

### Key Decisions

- Stdlib `csv` + dataclasses: collections are small, so keep dependencies light
- The summary prints counts only, never species (public logs)

---

## Feature: pvpoke-rankings-ingest

**Branch:** `feature/pvpoke-rankings-ingest`
**Depends on:** project-skeleton
**Status:** Merged (#4)
**Requires:** ai

### Goal

Fetch, validate and cache PvPoke Great, Ultra and Master League rankings.

### Acceptance Criteria

- [ ] Ranking URLs are defaults in `config/sources.toml` and can be overridden by env var
- [ ] With an `httpx.MockTransport` serving the fixture JSON, `fetch_rankings()` returns all three leagues keyed by species ID, with the fixture's entry counts
- [ ] A fixture missing a required field raises `SchemaError` naming the field and league
- [ ] After a fetch, the cache dir holds all three files. A second call with `offline=True`, using a transport that fails on any request, returns identical data.
- [ ] `pogo-triage fetch --offline` with an empty cache exits non-zero with a message telling the operator to run without `--offline`
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/sources/__init__.py` | Create | Shared fetch, cache and schema helpers |
| `src/pogo_triage/sources/pvpoke.py` | Create | League rankings ingest |
| `config/sources.toml` | Create | Upstream URL defaults |
| `src/pogo_triage/cli.py` | Modify | Add `fetch` command (`--offline`, `--cache-dir`) |
| `tests/fixtures/pvpoke_rankings_sample.json` | Create | Trimmed, real-shaped rankings |
| `tests/test_pvpoke.py` | Create | Fetch, schema and cache tests |

---

## Feature: game-data-and-cost-model

**Branch:** `feature/game-data-and-cost-model`
**Depends on:** pvpoke-rankings-ingest
**Status:** Held (deps)
**Requires:** ai

### Goal

Base stats (including mega forms), moves, CP/IV math, and power-up cost tables.

### Acceptance Criteria

- [ ] Loads base stats, types, mega forms and moves from the PvPoke gamemaster through the same fetch/cache/schema path (gamemaster URL in `config/sources.toml`)
- [ ] `cp(species, level, ivs)` matches at least 5 published reference values, with the test table citing its source
- [ ] `cost_to_level(current, target)` returns Stardust, Candy and XL Candy. Totals for 20→40 and 40→50 match the published totals, and shadow, purified and lucky multipliers change the results as published.
- [ ] `mega_forms()` returns both forms for a species with two megas and `[]` for a species with none
- [ ] `pogo-triage stats <species> --offline` exits 0 and prints stats and mega forms; an unknown species exits non-zero
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/sources/gamemaster.py` | Create | Gamemaster ingest: stats, types, megas, moves |
| `src/pogo_triage/costs.py` | Create | CP multipliers, CP/IV math, cost-to-level |
| `config/powerup_costs.toml` | Create | Per-level cost table and multipliers, with a source comment |
| `src/pogo_triage/cli.py` | Modify | Add `stats` command |
| `tests/fixtures/gamemaster_sample.json` | Create | Trimmed, real-shaped gamemaster |
| `tests/test_costs.py` | Create | CP and cost tests |
| `tests/test_gamemaster.py` | Create | Gamemaster parsing and mega lookup tests |

### Key Decisions

- Power-up costs live in config, so a game change means a config edit, not a code change

---

## Feature: scoring-engine

**Branch:** `feature/scoring-engine`
**Depends on:** pokegenie-csv-parser, game-data-and-cost-model
**Status:** Held (deps)
**Requires:** ai

### Goal

Per-Pokémon scores for raids, gym defense and three PvP leagues, a weighted composite, and a mega-potential flag.

### Acceptance Criteria

- [ ] `pogo-triage score --input tests/fixtures/pokegenie_sample.csv --offline --json out.json` exits 0 and writes, for every record, `raid`, `gym`, `great`, `ultra`, `master`, `composite` and `mega_potential`
- [ ] Ordering checks on fixture records: a known top-tier raid attacker outscores a known weak species on `raid`, and a shadow copy outscores an otherwise identical non-shadow copy on `raid`
- [ ] PvP is IV-rank aware: the fixture's rank-1 Great League IV spread scores higher on `great` than a 100% IV copy of the same species
- [ ] Weights come from `config/weights.toml` (raid highest by default). Swapping weights in a temp config changes the composite ranking as expected.
- [ ] `mega_potential` is true for a fixture species with a strong mega form (scored from the mega's stats) and false for a species with no mega
- [ ] Running the command twice produces byte-identical JSON
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/scoring.py` | Create | Raid and gym heuristics, composite, mega-potential |
| `src/pogo_triage/pvp_iv.py` | Create | League CP-cap IV rank computation |
| `config/weights.toml` | Create | Mode weights, mega threshold, shadow bonus |
| `src/pogo_triage/cli.py` | Modify | Add `score` command |
| `tests/test_scoring.py` | Create | Ordering, weights, mega and determinism tests |
| `tests/test_pvp_iv.py` | Create | IV-rank tests |

### Key Decisions

- The raid score is a documented in-repo heuristic built from stats, typing and the record's actual moves. There is no public raid-rankings API, so transparency beats false precision.
- `mega_potential` only answers "does this species' mega score well?" Bench redundancy (one active mega) is a later feature.

---

## Feature: verdicts-and-safeguards

**Branch:** `feature/verdicts-and-safeguards`
**Depends on:** scoring-engine
**Status:** Held (deps)
**Requires:** ai

### Goal

Turn scores into keep/invest/transfer verdicts with reasons, duplicate ranking, cost-aware invest picks and safeguard warnings.

### Acceptance Criteria

- [ ] `pogo-triage triage --input <fixture> --offline --json out.json` exits 0, and every record has `verdict` (`keep` / `invest` / `transfer`) and a non-empty `reason`
- [ ] A fixture species with three copies: the best copy is `keep` or `invest`, and the worst unprotected copy is `transfer`
- [ ] The only copy of a species is never `transfer` while the `last_copy` safeguard is on (the default)
- [ ] Every safeguarded fixture record (shiny, lucky, 100% IV, costume, shadow, legendary/mythical) has a verdict other than `transfer` and a `warnings` list. Turning a safeguard off in a temp config lets that record become `transfer`.
- [ ] Each `invest` record carries a target level and a cost equal to `cost_to_level()` for that record
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/verdicts.py` | Create | Verdicts, duplicate ranking, safeguards |
| `config/weights.toml` | Modify | Verdict thresholds, safeguard toggles, invest target levels |
| `src/pogo_triage/cli.py` | Modify | Add `triage` command |
| `tests/test_verdicts.py` | Create | Verdict, duplicate, last-copy and safeguard tests |

### Key Decisions

- Safeguards downgrade a verdict to `keep` with a warning. They are never hard blocks, per the operator's preference.

---

## Feature: html-report

**Branch:** `feature/html-report`
**Depends on:** verdicts-and-safeguards
**Status:** Held (deps)
**Requires:** ai

### Goal

A mobile-first, self-contained HTML report: new-catch triage first, whole collection second.

### Acceptance Criteria

- [ ] `pogo-triage run --input <fixture> --offline --out dist/ --today 2026-10-04` exits 0 and writes `dist/index.html`
- [ ] Parsed with `html.parser`, the new-catches section contains exactly the fixture records caught within `--since-days` (default 7), with transfer candidates listed first
- [ ] Parsed output: every safeguarded record's element carries the warning class, and every `mega_potential` record carries the mega badge
- [ ] Parsed output has no `<script src>` and no external `<link rel="stylesheet">`
- [ ] A fixture nickname containing `<script>` comes out escaped (Jinja2 autoescape on)
- [ ] Logs captured during `run` at the default level contain no fixture species names, nicknames or IVs
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/report.py` | Create | Render pipeline |
| `src/pogo_triage/templates/report.html.j2` | Create | Mobile-first template, inline CSS, narrow-viewport layout |
| `src/pogo_triage/cli.py` | Modify | Add `run`: ingest → score → verdicts → report |
| `tests/test_report.py` | Create | Parsed-HTML, escaping and log-hygiene tests |

### Key Decisions

- One self-contained file: the simplest Pages deploy, and it works offline once loaded

---

## Feature: gist-ingest

**Branch:** `feature/gist-ingest`
**Depends on:** html-report
**Status:** Ready (supervised)
**Requires:** both

### Goal

`pogo-triage run --gist` reads the collection CSV from a private gist using a read-only token.

### Acceptance Criteria

- [ ] With `POGO_GIST_ID` and `POGO_GIST_TOKEN` set and a `MockTransport`, `run --gist` exits 0. The test asserts the request URL and that the token goes only in the `Authorization` header.
- [ ] For a multi-file gist, it reads the file named by `POGO_GIST_FILE`, or the first `.csv` if unset
- [ ] A missing env var exits non-zero, naming the variable. A 401 or 404 response exits non-zero with a clear message.
- [ ] The token string never appears in stdout, stderr or captured logs in any of the above cases
- [ ] [HUMAN] The operator creates the private gist with a Poke Genie export, creates the fine-grained PAT (Gists: read-only), and stores `POGO_GIST_ID` and `POGO_GIST_TOKEN` as Actions secrets
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/ingest.py` | Create | Gist fetch, file selection, env config |
| `src/pogo_triage/cli.py` | Modify | `--gist` option on `run` |
| `tests/test_ingest.py` | Create | Mocked fetch, error paths, token-leak checks |

### Key Decisions

- A read-only gist token means the worst-case leak exposes Pokémon stats and nothing else

---

## Feature: actions-pipeline

**Branch:** `feature/actions-pipeline`
**Depends on:** gist-ingest
**Status:** Ready (supervised)
**Requires:** both

### Goal

A `workflow_dispatch` workflow that fetches the gist, runs the pipeline and deploys the report to Cloudflare Pages behind Access.

### Acceptance Criteria

- [ ] `tests/test_workflow.py` parses `.github/workflows/triage.yml` with PyYAML and asserts: the only trigger is `workflow_dispatch`; `permissions` is `contents: read`; there is no `actions/upload-artifact` step; and secrets are referenced only in the run and deploy steps
- [ ] The workflow installs from `pyproject.toml`, runs `pogo-triage run --gist --out dist/`, and deploys `dist/` with a pinned `wrangler pages deploy`
- [ ] CI runs `actionlint` on `.github/workflows/`
- [ ] `docs/SETUP.md` covers the gist, the PAT, the Pages project, the scoped API token, the four Actions secrets, and the Access application, step by step and doable from a phone
- [ ] [HUMAN] Cloudflare Pages project, scoped token and Access application (email one-time PIN, one address) created; `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` stored as secrets
- [ ] [HUMAN] From the GitHub app, dispatch the workflow; it goes green; the report opens on the phone after the Access PIN, reads without horizontal scrolling, and the new-catch counts match the app
- [ ] [HUMAN] `curl -sI` on the site from hub without an Access session returns a redirect to the Access login, not the report
- [ ] [HUMAN] The run's public log shows no species, nicknames or IVs
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/triage.yml` | Create | Dispatch: fetch, run, deploy |
| `.github/workflows/ci.yml` | Modify | Add actionlint |
| `docs/SETUP.md` | Create | One-time operator setup guide |
| `tests/test_workflow.py` | Create | Workflow structure and security assertions |
| `pyproject.toml` | Modify | Add PyYAML to dev extras |

### Notes

A gist edit can't trigger Actions, so manual dispatch is the intended phone flow. Secrets reach only this workflow; PR CI never sees them.

---

## Feature: raid-boss-ingest

**Branch:** `feature/raid-boss-ingest`
**Depends on:** html-report
**Status:** Held (deps)
**Requires:** ai

### Goal

Pull the current raid boss rotation from ScrapedDuck's raids JSON.

### Acceptance Criteria

- [ ] The raids URL is a default in `config/sources.toml`
- [ ] With a `MockTransport` serving the fixture, `fetch_bosses()` returns every boss with name, tier, types and shiny availability, and the test asserts the fixture's count
- [ ] Upstream 500 or schema drift: `pogo-triage run --input <fixture> --out dist/` still exits 0, writes the report, and logs one warning that teams were skipped
- [ ] `pogo-triage bosses --offline` with a cached file lists bosses and exits 0
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/sources/scrapedduck.py` | Create | Raids ingest with schema validation |
| `config/sources.toml` | Modify | Raids URL default |
| `src/pogo_triage/cli.py` | Modify | Add `bosses`; graceful skip in `run` |
| `tests/fixtures/scrapedduck_raids_sample.json` | Create | Real-shaped fixture |
| `tests/test_scrapedduck.py` | Create | Parse, drift and degrade tests |

---

## Feature: team-builder

**Branch:** `feature/team-builder`
**Depends on:** raid-boss-ingest
**Status:** Held (deps)
**Requires:** ai

### Goal

Raid teams of 6 from the collection: one per current boss, plus a standing team per attacking type, each with a sub-team and upgrade suggestions.

### Acceptance Criteria

- [ ] `pogo-triage teams --input <fixture> --bosses tests/fixtures/scrapedduck_raids_sample.json --offline --json out.json` exits 0 and writes a team for every fixture boss, plus a standing team for every attacking type the collection can field
- [ ] Every member of a boss team has a charged move that is super-effective against that boss, when the collection has 6 such Pokémon
- [ ] Duplicates are allowed: a fixture holding 6 copies of the best counter yields 6 identical-species slots
- [ ] A sub-team (the next best 6) is produced when there are at least 12 eligible Pokémon
- [ ] Each slot has an upgrade suggestion whose cost equals `cost_to_level()`; a slot already at its target level gets no suggestion
- [ ] `run` adds a raid-teams section. Parsed output lists current-rotation bosses first, then type teams.
- [ ] Running twice produces byte-identical JSON
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/pogo_triage/teams.py` | Create | Matchup scoring, selection, sub-teams, upgrade picks |
| `src/pogo_triage/report.py` | Modify | Teams in render context |
| `src/pogo_triage/templates/report.html.j2` | Modify | Raid-teams section |
| `src/pogo_triage/cli.py` | Modify | Add `teams`; wire into `run` |
| `tests/fixtures/pokegenie_teams.csv` | Create | Synthetic collection with duplicate counters |
| `tests/test_teams.py` | Create | Selection, duplicates, sub-team, upgrade and determinism tests |

### Key Decisions

- v1 ranks by type effectiveness × individual raid score, with no DPS/TDO simulation
- Duplicates are allowed by design. Diversifying toward six distinct species on a Stardust budget is a FEATURE-REQUESTS item.

---

## Feature: docs-readme

**Branch:** `feature/docs-readme`
**Depends on:** team-builder, actions-pipeline
**Status:** Ready (supervised)
**Requires:** ai

### Goal

A portfolio-quality README, written once the code exists.

### Acceptance Criteria

- [ ] The README covers what the tool does, the phone flow (export → gist → dispatch → report), a text architecture diagram, the scoring methodology with a link to the heuristic, data-source credits (PvPoke, ScrapedDuck/LeekDuck, Poke Genie), non-goals stated up front, and a pointer to `docs/SETUP.md`
- [ ] `tests/test_readme.py` extracts every `pogo-triage …` command from the README's usage section and runs it against fixtures with `--offline`; all exit 0
- [ ] Every relative link in `README.md` resolves to a file in the repo (test)
- [ ] All tests pass
- [ ] Lint clean

### Files to Create or Modify

| File | Action | Purpose |
|------|--------|---------|
| `README.md` | Create | Public documentation |
| `tests/test_readme.py` | Create | Executes documented commands, checks links |
