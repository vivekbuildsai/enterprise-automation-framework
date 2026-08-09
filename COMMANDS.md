# Enterprise Automation Framework — Command & Usage Guide

This document is the command-first reference for installing, configuring,
running, validating, discovering, synchronizing, reporting, testing, and
troubleshooting the framework. Every command below was run against this
repository's actual CLI output — nothing here is inferred from what an
option "should" look like. Where implementation and older docs disagreed,
implementation won; see [Notes on documentation drift](#notes-on-documentation-drift).

Not sure which document you need?

| Document | Answers |
|---|---|
| [README.md](README.md) | What is this product? |
| [docs/GettingStarted.md](docs/GettingStarted.md) | How do I get started? |
| **COMMANDS.md** (this file) | **What exactly do I type?** |
| [docs/ModularArchitecture.md](docs/ModularArchitecture.md) | How is the product engineered? |

## Contents

- [Install](#install)
- [Configure](#configure)
- [Doctor (environment preflight)](#doctor-environment-preflight)
- [Verify (quality gates)](#verify-quality-gates)
- [Run tests](#run-tests)
- [Discover (Application Discovery — optional)](#discover-application-discovery--optional)
- [Sync (Framework Sync — optional)](#sync-framework-sync--optional)
- [Extend an existing framework for a new UI (optional)](#extend-an-existing-framework-for-a-new-ui-optional)
- [Validate](#validate)
- [Report (Allure)](#report-allure)
- [Docker](#docker)
- [CI](#ci)
- [Debug / Troubleshoot](#debug--troubleshoot)
- [Using this framework from your own project](#using-this-framework-from-your-own-project)
- [Notes on documentation drift](#notes-on-documentation-drift)

---

## Install

### Command

```bash
git clone <repo-url> enterprise-automation-framework
cd enterprise-automation-framework
poetry install --no-root
poetry run python -m playwright install chromium firefox webkit
cp .env.example .env
```

### Purpose

Get a working development checkout: Python dependencies, the three
Playwright browser engines, and a starter `.env`.

### Prerequisite

Python 3.13, [Poetry](https://python-poetry.org/docs/#installation)
(`pipx install poetry`, not into a project venv).

### Output

An activated dependency set under Poetry's virtualenv and a local `.env`
you can edit. `--no-root` is this repo's own dev-workflow shortcut — it
skips installing the framework's *own* package metadata, which is correct
for developing inside this repo but not for consuming it as a dependency
(see [Using this framework from your own project](#using-this-framework-from-your-own-project)).

---

## Configure

### Command

```bash
cp .env.example .env
cp .env.dev.example .env.dev        # per-environment override; also available: .env.qa/.uat/.preprod/.production.example
```

### Purpose

Supply real values (`AUTOMATION_UI_BASE_URL`, `AUTOMATION_UI_USERNAME`,
`AUTOMATION_DB_*`, ...) without committing secrets.

### Prerequisite

None.

### Output

`.env` (shared defaults) and `.env.{environment}` (per-environment
overrides), both gitignored. Precedence, highest first: real process/CI
environment variables → `.env.{environment}` → `.env`.
`config/environments/{dev,qa,uat,preprod,production}.yaml` define the
config *shape* (`ui`, `ui_targets`, `api`, `database`, `clickhouse`,
`browser`, `auth`, `feature_flags`) — every value is `${AUTOMATION_VAR:-default}`.
See [docs/DatabaseConfiguration.md](docs/DatabaseConfiguration.md) for a
worked per-dialect example.

### Switch environment

```bash
AUTOMATION_ENV=qa poetry run pytest tests/regression -v
```

### Switch browser/headless

Edit `browser.browser` / `browser.headless` in `config/environments/<env>.yaml`.
Supported `browser` values: `chromium`, `chrome`, `edge`, `firefox`,
`safari` (WebKit engine — see [docs/Architecture.md](docs/Architecture.md)
for why real Safari.app can't be driven).

---

## Doctor (environment preflight)

Read-only environment capability check — Operating System/Architecture,
Python (+ virtual environment, Poetry), Node (node/npm/npx), browsers
(system Edge/Chrome/Firefox **and** Playwright-managed Chromium/Firefox/
WebKit — these are not the same thing, see
[docs/Architecture.md](docs/Architecture.md)), FFmpeg, Docker, Git
(repository/branch/working-tree-clean status). Run this on a new machine
before `discover`/`sync`/`extension` — every one of those already assumes
a working browser engine, and `doctor` is how you find out *before* a run
fails partway through instead of after.

### Command

macOS/Linux:

```bash
poetry run python -m framework doctor
poetry run python -m framework doctor --check
poetry run python -m framework doctor --fix
poetry run python -m framework doctor --fix --dry-run
poetry run python -m framework doctor --browser firefox
poetry run python -m framework doctor --report doctor_report.json

# Convenience wrapper (same command; no need to remember the module path)
scripts/doctor.sh --fix
```

Windows (Command Prompt — every line below runs as pasted, no `^` continuation needed):

```bat
poetry run python -m framework doctor
poetry run python -m framework doctor --check
poetry run python -m framework doctor --fix
poetry run python -m framework doctor --fix --dry-run
poetry run python -m framework doctor --browser firefox
poetry run python -m framework doctor --report doctor_report.json

REM Convenience wrapper
scripts\doctor.bat --fix
```

Windows (PowerShell):

```powershell
poetry run python -m framework doctor
poetry run python -m framework doctor --fix
poetry run python -m framework doctor --browser firefox

# Convenience wrapper
.\scripts\doctor.ps1 --fix
```

### Purpose

- Detects every capability this framework can use and prints a matrix of
  AVAILABLE/MISSING/DEGRADED/NOT_REQUIRED/UNSUPPORTED/BLOCKED per item,
  each with a `Reason`/`Remediation` line when it isn't simply AVAILABLE.
- Recommends one browser (bundled Chromium first, then Edge, Chrome,
  Firefox, WebKit) — or reports exactly why none is usable. `--browser
  <name>` requests one explicitly; if it isn't available, doctor says why
  and never silently substitutes a different engine.
- `--fix` proposes writing `AUTOMATION_BROWSER=<recommended>` to `.env`
  (this framework's existing config-override layer, already wired through
  `config/environments/<env>.yaml`'s `${AUTOMATION_BROWSER:-chromium}`) —
  never overwrites a differing existing value unless `--force` is also
  passed; `--dry-run` shows the same plan without writing anything.
- `--check` is an explicit, CI-friendly alias for the default behavior
  (both exit non-zero when a required capability is missing).

### Prerequisite

`poetry install --no-root` already run. Nothing else — doctor is designed
to work even in a partially configured environment; finding that out is
the point of running it.

### Output

The capability matrix + recommended browser + a one-line summary on
stdout; optionally a JSON `DoctorReport` via `--report <path>`. Exit code
`0` when every *required* capability is present, `3` when one is missing
— the same code `extension run` uses for its own preflight stage (see
[Extend an existing framework for a new UI](#extend-an-existing-framework-for-a-new-ui-optional)),
so CI can treat exit code `3` uniformly as "environment problem" from
either entry point.

---

## Verify (quality gates)

Run these before pushing — they're the exact commands CI's `lint` job runs.

### Command

```bash
poetry run black --check framework tests      # drop --check to auto-format in place
poetry run ruff check framework tests --fix
poetry run mypy framework
poetry run bandit -r framework -c pyproject.toml
poetry run pre-commit install                 # one-time; runs black/ruff/mypy/bandit + hygiene hooks automatically on commit
poetry run pre-commit run --all-files          # run every configured hook once, on demand
```

### Purpose

Format check, lint, static type check, security scan, and (optionally)
wire them into git hooks.

### Prerequisite

`poetry install --no-root` already run.

### Output

Zero-exit-code on a clean repo. `mypy` only checks `framework/` (`strict = true`,
332 files as of this writing) — `tests/`/`examples/` are intentionally out
of its scope. `bandit` excludes `tests/`, `reports/`, `artifacts/`, `.venv/`.

---

## Run tests

### Command

```bash
# By suite (mirrors tests/<suite>/ layout)
poetry run pytest tests/smoke -v
poetry run pytest tests/negative tests/accessibility tests/visual -v
poetry run pytest tests/e2e -v                                            # real: subscriber_management; skipped: 6 skeleton modules
poetry run pytest tests/api -v --alluredir=reports/allure-results
poetry run pytest tests/database -m "database and not integration" -v     # SQLite, zero setup
poetry run pytest tests/database/integration -m hybrid -v                 # Hybrid UI+API+DB
poetry run pytest tests/network -v
poetry run pytest tests/testdata -v

# Parallel
poetry run pytest tests/smoke -n auto

# Against a specific environment
AUTOMATION_ENV=qa poetry run pytest tests/regression -v

# With coverage (as CI does for the API suite)
poetry run coverage run --source=framework/api -m pytest tests/api -m api
poetry run coverage report -m --fail-under=90
```

### Purpose

Run the framework's own test suite by layer/marker.

### Prerequisite

`poetry install --no-root`; Playwright browsers installed for UI-touching
suites; `AUTOMATION_UI_BASE_URL`/`AUTOMATION_DB_*`/etc. configured (defaults
in `.env.example` already point at public, zero-setup targets:
the-internet.herokuapp.com, dummyjson.com, in-memory SQLite).

### Output

Standard pytest console output; `reports/allure-results/*.json` when
`--alluredir` is passed; failure-only artifacts (screenshot/trace/video)
under `artifacts/` (see [Debug / Troubleshoot](#debug--troubleshoot)).

### Run the runnable examples

```bash
poetry run pytest examples/ -v
```

Seven small, executable examples (UI, UI+network+DB, UI+API+DB, Framework
Sync, Discovery, AI). See [examples/README.md](examples/README.md) —
**not** part of `tests/` (`testpaths = ["tests"]` never auto-collects
them), so this is the only way to run them.

---

## Discover (Application Discovery — optional)

Read-only introspection of a real UI page, an OpenAPI spec, or a
configured database — never writes to the target.

### Command

```bash
poetry run python -m framework.discovery ui <url> --report report.json [--crawl --max-pages 5] [--headed] [--capture-network --network-url-pattern "**/*"]
poetry run python -m framework.discovery api <openapi.json> --report report.json
poetry run python -m framework.discovery db <db_key> --env dev --report report.json
poetry run python -m framework.discovery generate --report report.json --output-dir generated/
poetry run python -m framework.discovery recommend --report report.json --env dev --output recommendations.json

# Also reachable via the unified dispatcher:
poetry run python -m framework discover ui <url> --report report.json
```

### Purpose

- `ui`/`api`/`db` each **append** to the same `--report` file (creating it
  if missing) — a full pass against one application is typically all
  three run against the same file, then hand-review the JSON.
- `generate` turns discovered **pages** and **tables** into Page
  Object/domain-model code under `--output-dir` (discovered **endpoints**
  don't generate code — verified: a report containing only endpoints
  produces `0 file(s) written`).
- `recommend` is optional (gated by `ai.enabled` in
  `config/environments/<env>.yaml`) — asks the configured `AIProvider` for
  a suggested name/description per element. With AI disabled it still
  runs and writes recommendations, each carrying
  `RecommendationConfidence.DISCOVERED` instead of `AI_SUGGESTED` (verified:
  `provider 'disabled'` in the printed output).

### Prerequisite

`ui` needs a real reachable URL and Playwright installed; `db` needs a
configured `database.<db_key>` entry for `--env`; only run `ui`/`db`
against an application/database you're authorized to access.

### Output

`--report` (default `discovery_report.json`) — a `DiscoveryReport` JSON
document. `generate` writes `.py` files under `--output-dir` (default
`generated/`, gitignored) — review before use, never auto-applied.

---

## Extend an existing framework for a new UI (optional)

Use this read-only-by-default workflow when a customer has a mature
automation suite but introduces a new UI on the same backend. It
inventories existing assets, discovers the new UI, classifies and
deduplicates every network call the new UI actually made (so CSS/JS/image/
analytics/third-party noise and authentication traffic are never mistaken
for application API evidence), scores how trustworthy the discovery run
itself is (a login-page redirect is a real, detected outcome — not a
silent false positive), writes a human-reviewable reuse/extension plan,
and — only after explicit approval — generates a framework-native
scaffold for whatever genuinely needs to be created. Neither the existing
repository nor the new UI is ever modified.

### One-command workflow: `extension run`

The recommended entry point — runs every stage in order (environment
preflight → analyze the existing framework → discover the new UI →
classify/deduplicate network calls → score discovery quality → correlate
against the existing capability catalog → build the extension plan →
safety gate → optional scaffold) and writes everything under a single
timestamped `<output-dir>/<UTC timestamp>/` directory. Never generates
scaffold code without `--scaffold`, and even then only after the
safety gate passes and the write is explicitly confirmed.

macOS/Linux:

```bash
# Analysis only — the default; nothing is ever written outside --output-dir.
poetry run python -m framework.extension run \
  --framework <existing-framework-path> --url <new-ui-url> \
  --output-dir extension-output

# Also generate scaffold code, with an interactive y/N confirmation before
# any file is written.
poetry run python -m framework.extension run \
  --framework <existing-framework-path> --url <new-ui-url> \
  --scaffold --output-dir extension-output

# Non-interactive (CI): skip the confirmation prompt, allow uncommitted
# changes in the current working tree, preview only (no files written).
poetry run python -m framework.extension run \
  --framework <existing-framework-path> --url <new-ui-url> \
  --scaffold --yes --allow-dirty --dry-run --output-dir extension-output

# Convenience wrapper (same command, forwards every argument as-is)
scripts/extension-run.sh --framework <existing-framework-path> --url <new-ui-url> --scaffold
```

Windows (Command Prompt — every line below runs as pasted, no `^` continuation needed):

```bat
poetry run python -m framework.extension run --framework <existing-framework-path> --url <new-ui-url> --output-dir extension-output

poetry run python -m framework.extension run --framework <existing-framework-path> --url <new-ui-url> --scaffold --output-dir extension-output

poetry run python -m framework.extension run --framework <existing-framework-path> --url <new-ui-url> --scaffold --yes --allow-dirty --dry-run --output-dir extension-output

REM Convenience wrapper
scripts\extension-run.bat --framework <existing-framework-path> --url <new-ui-url> --scaffold
```

Windows (PowerShell):

```powershell
poetry run python -m framework.extension run --framework <existing-framework-path> --url <new-ui-url> --output-dir extension-output

poetry run python -m framework.extension run --framework <existing-framework-path> --url <new-ui-url> --scaffold --output-dir extension-output

# Convenience wrapper
.\scripts\extension-run.ps1 --framework <existing-framework-path> --url <new-ui-url> --scaffold
```

#### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — analysis complete (and scaffold written, if `--scaffold` was requested and approved) |
| 1 | Unexpected/unhandled error (missing file, invalid argument value, corrupt archive, ...) |
| 2 | Usage error — argparse's own default for invalid CLI arguments |
| 3 | Environment preflight failed (`framework doctor`) — skip with `--skip-doctor` |
| 4 | Discovery quality is `BLOCKED` — this looks like an authentication redirect, not the real application; the run stops before any scaffold stage, whether or not `--scaffold` was passed |
| 5 | Git working tree is dirty and `--allow-dirty` was not passed (only checked when `--scaffold` is requested) |
| 6 | `--scaffold` was requested but declined — `--dry-run`, or no `--yes` and the answer wasn't `y` (a missing `--yes` on a non-interactive stdin is always treated as declined, never hangs waiting for input) |

#### Safety gate: discovery quality

Every run scores its own discovery quality (`HIGH_CONFIDENCE`/`PARTIAL`/
`LOW_CONFIDENCE`/`BLOCKED`) from concrete signals: whether the requested
page turned out to be a login page (redirect detection), what fraction of
discovered pages look like login pages, whether any interactive elements
were found at all, and whether classification found any real application
API traffic. `BLOCKED` — e.g. discovery only ever reached a login page —
stops the run with exit code 4 and an explicit warning, before scaffold
ever runs, rather than silently producing a report built entirely from
authentication-redirect noise.

### Advanced: manual step-by-step (analyze / scaffold separately)

Useful for CI steps that need to inspect the intermediate reports, or
reuse an already-computed `sync analyze`/`discover ui` report instead of
re-running discovery.

```bash
# Equivalent to `extension run`'s analysis stages, but writes wherever
# you point it instead of a timestamped directory.
# --capture-network is always on for the discovered UI here; it stores
# shape only (HTTP method/path/status and parameter/key names), never
# values, headers, or credentials.
poetry run python -m framework extension analyze \
  --framework <existing-framework-path> \
  --url <new-ui-url> \
  --sync-report existing.json --discovery-report new-ui.json \
  --output extension-plan.json

# Advanced: reuse already-computed reports instead (e.g. from a separate
# `sync analyze` / `discover ui --capture-network` run, or a CI rerun).
poetry run python -m framework sync analyze <existing-framework-path> --report existing.json
poetry run python -m framework discover ui <new-ui-url> --capture-network --report new-ui.json
poetry run python -m framework extension analyze --sync-report existing.json --discovery-report new-ui.json --mode reuse-analysis --output reuse.json

# Optional advisory AI suggestions for MANUAL_REVIEW/UNKNOWN items only.
poetry run python -m framework extension analyze --sync-report existing.json --discovery-report new-ui.json --mode ai-recommendations --ai-output suggestions.json --output extension-plan.json
```

The extension report classifies each item as `REUSE_EXISTING`,
`EXTEND_EXISTING`, `CREATE_NEW`, `UNKNOWN`, or `MANUAL_REVIEW`, with source
evidence and a `confidence` score (0-100), and prints a REUSE MATRIX
summary. API matches require endpoint and HTTP-method evidence;
table/path matches are possible DB reuse candidates, not proof of data
lineage. `analyze`'s report also carries the same `network_classification`
(raw/deduplicated/classified call counts) and `discovery_quality` data
`extension run` prints — inspect `extension-plan.json` directly for the
full detail. Review the report before scaffolding anything.

### Framework-native scaffolding (optional, human-approved)

The manual/standalone form of the same scaffold stage `extension run
--scaffold` runs automatically — use this when you already have separate
`extension-plan.json`/`existing.json`/`new-ui.json` files (e.g. from CI)
and want scaffold as its own step. Generates NEW automation — Page Object + test — only for items the
extension plan classified `CREATE_NEW`/`EXTEND_EXISTING`, only in the
existing repository's own detected language/framework/test-runner style
(Java+Selenium+TestNG, Java+Selenium+JUnit, Python+pytest+Playwright,
TypeScript+Playwright, or Robot Framework — anything else falls back to a
README-only plan rather than fabricating code in the wrong ecosystem).
Existing, already-reusable capabilities are referenced by name and source
file in a comment — never duplicated as a second implementation.

```bash
# Always a preview first (no files written) — inspect before approving.
poetry run python -m framework extension scaffold \
  --extension-report extension-plan.json \
  --sync-report existing.json --discovery-report new-ui.json \
  --output-dir generated/extension

# Explicit human approval writes the files (plus extension-manifest.json).
poetry run python -m framework extension scaffold \
  --extension-report extension-plan.json \
  --sync-report existing.json --discovery-report new-ui.json \
  --output-dir generated/extension --approve

# --overwrite is required to replace files already at the generated paths;
# without it, a conflicting path fails the whole write (never partial).
```

`--output-dir` must resolve inside `framework.project_root.PROJECT_ROOT`
(the customer's own project) — never inside this package's installed
location. Every generated file carries a `GENERATED SCAFFOLD — REVIEW
REQUIRED` notice and `TODO` markers for anything not itself confirmed
evidence (an unlabeled locator, an assumed API mapping, a DB assertion,
authentication state). Run the customer's own normal test command against
the reviewed output — nothing here is ever labeled production ready.

---

## Sync (Framework Sync — optional)

Analyze an **existing** (non-this-framework) test automation repo and
produce a human-reviewed migration worksheet. Only Mode 1 (analyze,
read-only) and Mode 2 (scaffold — worksheet, never source code) are
implemented — Modes 3/4 (auto-migrate/auto-sync) are intentionally not,
see [docs/FrameworkSync.md](docs/FrameworkSync.md).

### Command

```bash
poetry run python -m framework.sync analyze <source> --report analysis.json
poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/ [--scope {repository,directory,suite,tag,class,test} --selector <value>] [--recommendations recs.json]
poetry run python -m framework.sync diff <before.json> <after.json>
poetry run python -m framework.sync recommend --report analysis.json --env dev --output recs.json

# Also reachable via the unified dispatcher:
poetry run python -m framework sync analyze <source> --report analysis.json
```

### Purpose

- `analyze` — `<source>` is a local directory, a `.zip` archive, or a git
  URL (`https://`, `http://`, `git@`, `ssh://`, or `file://` — all four
  route through `git clone`; a plain path routes through local-directory
  analysis). Never modifies the source, never executes anything in it.
  Prints an "EXISTING AUTOMATION INVENTORY" — tests/classes/suites/tags/
  Page Objects/API clients/execution model, all evidence-based (a source
  file is never counted as a test merely because it exists) — see
  [docs/FrameworkSync.md](docs/FrameworkSync.md) for what counts as
  evidence per technology.
- `scaffold` — generates `<output-dir>/MIGRATION_WORKSHEET.md` from a saved
  analysis; optionally folds in a `recommend` output as a separate,
  clearly-labeled, unverified section. Default `--scope repository`
  covers every detected test without migrating any of it (Mode C, "Full
  Modernization Analysis"); `--scope {directory,suite,tag,class,test}
  --selector <value>` restricts the worksheet's "Migration candidates"
  section to exactly that subset, leaving every other test unmentioned
  and untouched (Mode B, "Selective Migration").
- `diff` — compares two saved analyses (e.g. before/after a migration
  sprint): new/removed frameworks, file-count delta, new/resolved findings.
- `recommend` — optional, AI-gated exactly like `discovery recommend`.

### Prerequisite

For a git-URL source, `git` on PATH and network/repo access. For `file://`,
a real local git repository (not just a directory — `file://` is a `git
clone` remote, verified against a real local repo).

### Output

`--report` (default `repository_analysis.json`) — a `RepositoryAnalysis`
JSON document. `scaffold` writes only into `--output-dir` (default
`generated/`, gitignored).

### Multi-Language & Multi-Framework analysis

`analyze` is language/framework-agnostic — the **same command** works
regardless of what the target repository is written in; language and
framework are detected automatically, never passed as a flag. Verified
against real sanitized fixtures (`tests/sync/fixtures/`) covering Java,
TypeScript, Python, C#, and Robot Framework — see
[docs/FrameworkSync.md](docs/FrameworkSync.md) for the full support
matrix.

```bash
# Java + Selenium + TestNG
poetry run python -m framework.sync analyze tests/sync/fixtures/java_selenium_testng --report analysis.json
# -> Analyzed 5 files (Java). 0/3 detected technologies are fully
#    supported, 1 partially supported, 2 require manual review.
#    Tests Detected: 3, Test Classes: 2, Test Suites: 1 (testng.xml),
#    Tags/Groups: regression, smoke, ui — Parallelism: 4 (from
#    testng.xml), Primary Execution: mvn test -Dsurefire.suiteXmlFiles=testng.xml

# TypeScript + Playwright
poetry run python -m framework.sync analyze tests/sync/fixtures/typescript_playwright --report analysis.json
# -> Analyzed 3 files (TypeScript). 1/1 detected technologies are fully
#    supported. Tests Detected: 2, Primary Execution: playwright test

# Python + Selenium
poetry run python -m framework.sync analyze tests/sync/fixtures/python_selenium --report analysis.json
# -> Analyzed 2 files (Python). 0/1 detected technologies are fully
#    supported, 1 partially supported. Tests Detected: 0 — this fixture
#    is unittest-based, not pytest-based; only pytest test-level
#    extraction is implemented today (see "Remaining gaps" in
#    docs/FrameworkSync.md), the framework itself is still detected.

# C# + Selenium + NUnit
poetry run python -m framework.sync analyze tests/sync/fixtures/csharp_selenium_nunit --report analysis.json
# -> Analyzed 2 files (C#). 0/2 detected technologies are fully
#    supported, 1 partially supported, 1 require manual review.

# Robot Framework + SeleniumLibrary (a keyword-driven DSL, not "Python" —
# gets its own language bucket and structural analysis, see FrameworkSync.md)
poetry run python -m framework.sync analyze tests/sync/fixtures/robot_selenium_library --report analysis.json
# -> Analyzed 3 files (Robot Framework). 0/3 detected technologies are
#    fully supported, 2 partially supported, 1 require manual review.
#    Tests Detected: 2, Reusable Keywords: 2, Test Suites: 1
```

Each `analysis.json` includes the full language breakdown (not just the
primary language — a mixed-language repository is never collapsed to
one), every detected technology with its own `support_level` and
evidence, an "EXISTING AUTOMATION INVENTORY" (see docs/FrameworkSync.md),
and — for a Robot Framework repository — a `robot_structure` block
(Test Case/Keyword/Resource-file/Variable counts, libraries,
Setup/Teardown presence). Run `scaffold` against any of these
`analysis.json` files to see the corresponding migration worksheet,
including its "Cross-language mapping" and "Migration candidates"
sections.

### Selective migration (Mode B) — a subset of a large existing suite

```bash
# Only the tests tagged "smoke" — the other tests in the same repository
# are never listed or implied to need any action.
poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/ \
    --scope tag --selector smoke

# One specific class/suite/test:
poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/ \
    --scope class --selector DashboardTest
poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/ \
    --scope test --selector "src/test/java/LoginTest.java::LoginTest::validLoginReachesSecureArea"
```

Any `--scope` other than the default `repository` requires `--selector`
— omitting it fails cleanly (`Error: Migration scope 'tag' requires a
--selector value.`, exit code 1) rather than silently falling back to
the whole repository.

---

## Validate

Ad-hoc field-by-field comparison of two JSON files from the shell — a CLI
wrapper around `DataComparator.compare()`.

### Command

```bash
poetry run python -m framework validate --expected expected.json --actual actual.json [--fields a,b,c] [--timing]
```

### Purpose

Case/whitespace-insensitive comparison; exits `0` on match, `1` on
mismatch (verified: a real mismatch prints `expected vs actual: MISMATCH`
plus a per-field diff, e.g. `- total: 100 != 105`, and returns exit code 1).
`--fields` restricts to a comma-separated field list (default: keys
present in both files). `--timing` prints a phase-timing summary + run ID
to stderr.

This CLI subcommand does **not** expose a tolerance flag — for numeric
percentage/absolute tolerance, call `DataComparator.compare(...,
tolerance=Tolerance(...))` directly from Python (see
[examples/data_validation](examples/data_validation)).

### Prerequisite

Two readable JSON files.

### Output

A human-readable comparison report on stdout; exit code `0`/`1`.

---

## Report (Allure)

### Command

```bash
poetry run pytest tests/smoke --alluredir=reports/allure-results   # any suite — write results as it runs
poetry run allure serve reports/allure-results                     # requires the Allure CLI installed separately
poetry run python -m framework report generate --results-dir reports/allure-results --output-dir reports/allure-report
poetry run python -m framework report open --output-dir reports/allure-report
```

### Purpose

`report generate`/`report open` are thin wrappers around the external
`allure generate`/`allure open` CLI commands. Verified: without the Allure
CLI installed, `report generate` fails gracefully with `The 'allure' CLI
isn't installed/on PATH. Install it (...) or use the 'allure-report'
docker-compose service instead.` and exit code `1` — it does not crash
with a raw traceback.

### Prerequisite

Existing `reports/allure-results/` (from a prior `--alluredir` run) and,
for `report`/`allure serve`, the [Allure CLI](https://allurereport.org/docs/install/)
on PATH — or skip installing it and use the Docker service instead:

```bash
docker compose up -d allure-report   # serves on http://localhost:5050
```

### Output

`reports/allure-report/` (static HTML report) for `generate`; a served
report in a browser for `open`/`allure serve`/the Docker service. Failed
database validations attach SQL text, elapsed time, row count, and
comparison diff automatically (`framework.database.telemetry`).

---

## Docker

### Command

```bash
docker build -f docker/Dockerfile -t enterprise-automation-framework:local .
docker compose run --rm automation                    # tests/smoke by default
docker compose run --rm api-tests                      # tests/api
docker compose up -d postgres mysql                     # real DB backends, then:
docker compose run --rm database-tests                  # tests/database against Postgres
docker compose run --rm hybrid-tests                     # tests/database/integration (UI+API+DB)
docker compose up -d allure-report                       # Allure Docker service, :5050
docker compose --profile oracle up -d oracle-xe          # optional, needs the `oracle` poetry group
```

### Purpose

Containerized execution — no local Python/Playwright/DB install needed
beyond Docker itself. Each `docker-compose.yml` service pre-wires the
matching env vars and pytest invocation (source of truth: `docker-compose.yml`).

### Prerequisite

Docker (and Docker Compose) installed and running.

### Output

`./artifacts`, `./reports`, `./logs` on the host via volume mounts
(defined per-service in `docker-compose.yml`) — same paths a local run
would produce.

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs: `lint` (Black/Ruff/MyPy/Bandit)
→ `test` (UI suites: smoke/negative/accessibility/visual/e2e, matrixed) +
`test-api` (with coverage, ≥90% gate) + `test-database` (SQLite/PostgreSQL/MySQL
matrix, real service containers) + `test-hybrid` + `test-testdata`, all in
parallel → `report` (aggregated Allure) → `docker` (image build + smoke
verification inside the built image, gated on `main`). Every job command
above is one you can run locally — CI does not do anything a local
`poetry run ...` invocation can't reproduce.

---

## Debug / Troubleshoot

### Command

```bash
# Inspect a failed test's captured artifacts (screenshot/trace/video) — only written on failure
ls artifacts/screenshots/ artifacts/traces/

# Open a Playwright trace file
poetry run playwright show-trace artifacts/traces/<test_name>.zip

# Re-run one test verbosely (real example — swap in your own path::test)
poetry run pytest "tests/smoke/test_login_smoke.py::TestLoginSmoke::test_valid_login_reaches_secure_area" -v -s
```

### Purpose

Locate and inspect failure evidence. Artifacts are only captured on
failure by design (`DriverManager.finalize`) — a flaky test that passes on
retry leaves nothing behind for the failed attempt.

### Prerequisite

A prior test run that failed with `screenshot_on_failure`/`trace_on_failure`
enabled (both default `true` in `BrowserConfig`).

### Output

A `.png` screenshot, a Playwright `.zip` trace (open with `playwright
show-trace` or [trace.playwright.dev](https://trace.playwright.dev)), and
optionally a `.webm` video, all under `artifacts/`.

See [docs/Troubleshooting.md](docs/Troubleshooting.md) for known error
messages (`ScopeMismatch`, Bandit false positives, `poetry install`
pruning itself, missing Docker system libraries) and their fixes.

---

## Using this framework from your own project

This file covers commands run *inside* this repo. Installing the
framework as a dependency into your **own** separate project (Poetry/pip
install, zero-conftest fixture auto-discovery, the 10-step customer
journey from install through UI+API+DB validation and analyzing an
existing framework) is covered in
[docs/GettingStarted.md § Using this framework from your own project](docs/GettingStarted.md#using-this-framework-from-your-own-project) —
not duplicated here.

---

## Notes on documentation drift

Found and corrected while writing this guide, by checking implementation
against docs rather than assuming either was right:

- `framework validate` has **no tolerance flag** — some intuition might
  expect one given `DataComparator` supports `Tolerance`; the CLI only
  does exact (normalized) comparison. Documented explicitly above so this
  isn't rediscovered by trial and error.
- `discovery generate` silently writes **0 files** for a report containing
  only API endpoints (it only generates from `pages`/`tables`) — not
  previously called out anywhere; documented above under
  [Discover](#discover-application-discovery--optional).
- No other discrepancy between `--help` output, source, and existing docs
  was found — every command in this guide was executed against this
  checkout, not inferred from its docstring.
