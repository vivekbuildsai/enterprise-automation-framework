# Framework Maintenance Guide

This is the operational manual for this enterprise automation framework. It lists **every configurable
file** in the repository, explains **when** it should change, **who** is expected to change it, and
gives a **real example** for each. If you're onboarding onto this framework, start here — it tells
you where to look before you touch code.

This guide describes files as they exist today. If a file listed here has moved or a new
configurable file has been added since, treat this document itself as something to update (see
[§15 Keeping This Guide Current](#15-keeping-this-guide-current)).

---

## 1. Who's who

Two roles are used throughout this guide. Most repos don't need the distinction, but this one does
— getting it backwards is how a framework accumulates either "every test has its own copy of the
timeout" (nobody owns shared config) or "I can't add my module's test data without asking permission"
(too much gatekeeping).

| Role | Owns | Typically does NOT touch |
|---|---|---|
| **Automation Engineer** | Writing/maintaining tests and Page Objects for *their* business module. The day-to-day user of the framework. | Pydantic config schemas, CI/CD pipeline definitions, Docker images, dependency versions, linting rules |
| **Framework Maintainer** | The shared architecture: config schema, CI/CD, Docker, dependencies, code-quality tooling, cross-cutting constants/components. | Module-specific test data, per-module pytest markers' *usage*, individual environment credential values |

Several files below are touched by **both**, but for different kinds of change — e.g. an automation
engineer adds a new `api.<service>` block to `dev.yaml` using the existing schema; a framework
maintainer is the one who changes the schema itself (`framework/config/models.py`) when a genuinely
new *kind* of field is needed. Each section below says explicitly which is which.

---

## 2. Quick reference

| File / path | Purpose | Who changes it | Committed to git? |
|---|---|---|---|
| `.env` | Shared secrets/defaults, every environment | Automation Engineer | ❌ (gitignored; `.env.example` is) |
| `.env.{environment}` | Per-environment overrides (BASE_URL, credentials, timeouts) | Automation Engineer | ❌ (gitignored; `.env.{environment}.example` is) |
| `config/environments/*.yaml` | Environment definitions — which API/DB/UI targets exist, feature flags | Both (see §4) | ✅ |
| `config/dashboards/*.json` | ClickHouse dashboard/widget query catalogs | Automation Engineer (adding queries with real evidence) | ✅ |
| `framework/constants/timeouts.py` | Global default timeouts/retry counts | Framework Maintainer | ✅ |
| `pyproject.toml` → `[tool.pytest.ini_options]` markers | Registers pytest markers (`smoke`, `subscriber_management`, ...) | Automation Engineer (new module marker), Framework Maintainer (cross-cutting marker) | ✅ |
| `pyproject.toml` → `[tool.poetry.dependencies]` | Runtime/dev dependency versions | Framework Maintainer | ✅ |
| `pyproject.toml` → `[tool.black]` / `[tool.ruff]` / `[tool.mypy]` / `[tool.bandit]` | Code-quality tool configuration | Framework Maintainer | ✅ |
| `.pre-commit-config.yaml` | Pre-commit hook versions/args | Framework Maintainer | ✅ |
| `.github/workflows/ci.yml` | CI pipeline: jobs, matrices, env vars | Framework Maintainer | ✅ |
| `docker-compose.yml` | Local service definitions (Postgres/MySQL/Oracle, app containers) | Framework Maintainer | ✅ |
| `docker/Dockerfile` | Runtime image build | Framework Maintainer | ✅ |
| `tests/conftest.py` | Registers fixture plugin modules | Framework Maintainer (new fixture *layer*) | ✅ |
| `.gitignore` | What never gets committed | Framework Maintainer | ✅ |

---

## 3. Environment & secrets configuration

### 3.1 `.env`

**What it is**: shared secrets and defaults that apply across every environment unless a
`.env.{environment}` file overrides them. Loaded by `framework/config/settings.py::get_settings()`.

**When to change it**: whenever you need a *new* environment variable that isn't yet defined, or
you're setting up this repo locally for the first time (`cp .env.example .env`).

**Who changes it**: **Automation Engineer** — this is your local secrets file. Never shared, never
committed (`.gitignore` blocks it; only `.env.example` is tracked).

**Example** (from `.env.example`, the tracked template you copy from):
```bash
AUTOMATION_ENV=dev

AUTOMATION_UI_BASE_URL=https://the-internet.herokuapp.com
AUTOMATION_UI_USERNAME=tomsmith
AUTOMATION_UI_PASSWORD=SuperSecretPassword!

AUTOMATION_API_SUBSCRIBER_URL=https://api.dev.example.com/subscriber
AUTOMATION_API_CLIENT_ID=
AUTOMATION_API_CLIENT_SECRET=

# ui_only | ui_api | ui_database | ui_api_database
AUTOMATION_VALIDATION_MODE=ui_api_database

# postgresql | mysql | oracle | mssql | sqlite
AUTOMATION_DB_DIALECT=sqlite
AUTOMATION_DB_NAME=:memory:
```

**Rule**: if you add a new `AUTOMATION_*` variable that every environment needs a *default* for, add it to
`.env.example` too (with a placeholder, never a real value) so the next engineer knows it exists.

### 3.2 `.env.{environment}`

**What it is**: per-environment overrides layered *on top of* `.env`. Precedence (highest first):
real process/CI environment variable → `.env.{environment}` → `.env`. See
`framework/config/settings.py::get_settings()` for the exact resolution logic.

**When to change it**: when a value genuinely differs per environment — BASE_URL, USERNAME,
PASSWORD, BROWSER, HEADLESS, timeouts, or a real internal target (e.g. `AUTOMATION_APP_BASE_URL`,
`AUTOMATION_CLICKHOUSE_*`) that only some environments can reach.

**Who changes it**: **Automation Engineer** — same secrets-file rule as `.env`: never committed,
copy from the tracked `.env.{environment}.example`.

**Example** (`.env.dev.example`, real content):
```bash
AUTOMATION_UI_BASE_URL=https://the-internet.herokuapp.com
AUTOMATION_UI_USERNAME=tomsmith
AUTOMATION_UI_PASSWORD=SuperSecretPassword!

AUTOMATION_BROWSER=chromium
AUTOMATION_HEADLESS=true
AUTOMATION_ACTION_TIMEOUT_MS=15000
AUTOMATION_NAVIGATION_TIMEOUT_MS=30000

# A real target application — private network, unset by default
# AUTOMATION_APP_BASE_URL=http://<internal-host>:<port>
# AUTOMATION_APP_USERNAME=<username>
# AUTOMATION_APP_PASSWORD=<password>
```

**Rule**: every real value (an actual internal IP, a real password) lives **only** here, never in
`config/environments/*.yaml` — that file is tracked and reviewed by everyone. If you catch yourself
about to type a real credential into a `.yaml` file, stop; it belongs in `.env.{environment}`
instead, referenced via `${VAR:-}`.

---

## 4. Environment definitions — `config/environments/*.yaml`

**What it is**: one file per environment (`dev.yaml`, `qa.yaml`, `uat.yaml`, `preprod.yaml`,
`production.yaml`) declaring which UI/API/database/ClickHouse targets exist for that environment,
plus browser and feature-flag defaults. Every value is either a literal (safe to commit — a
timeout, a boolean) or an `${ENV_VAR:-default}` placeholder (for anything that might be
environment- or secret-specific). Loaded and validated against `framework/config/models.py`'s
Pydantic schema.

**When to change it**:
- **Add a block using the existing schema** (a new `api.<name>`, `database.<name>`,
  `clickhouse.<name>`, or `ui_targets.<name>` entry) → this is normal, frequent, module-level work.
- **Change what fields a section supports** (e.g. adding a new field to `ClickHouseConfig`) →
  requires a schema change in `framework/config/models.py` first (see §4.1 below).

**Who changes it**:
- **Automation Engineer** adds a new named target for their own module, using fields that already
  exist in the schema.
- **Framework Maintainer** changes `framework/config/models.py` when a genuinely new *kind* of
  setting is needed (a config field that doesn't exist on any model yet).

**Example — adding a new API target** (`dev.yaml`, real pattern already used):
```yaml
api:
  subscriber_management:
    base_url: "${AUTOMATION_API_SUBSCRIBER_URL:-https://api.dev.example.com/subscriber}"
    timeout_seconds: 30
    auth_type: bearer
    client_id: "${AUTOMATION_API_CLIENT_ID:-}"
    client_secret: "${AUTOMATION_API_CLIENT_SECRET:-}"
```
To add a new one for your own service, copy this block, rename the key, and point the `${VAR:-}`
placeholders at new env var names you also add to `.env.example`.

**Example — adding a new UI target** (the actual pattern already used, `dev.yaml`):
```yaml
ui_targets:
  target_app:
    base_url: "${AUTOMATION_APP_BASE_URL:-}"
    login_username: "${AUTOMATION_APP_USERNAME:-}"
    login_password: "${AUTOMATION_APP_PASSWORD:-}"
```
`base_url` is nullable here (`OptionalUiConfig`, not `UiConfig`) — an unconfigured target doesn't
fail settings load, it just means any fixture/test that needs it should `pytest.skip()` when the
target isn't configured for the current environment.

### 4.1 The schema behind it — `framework/config/models.py`

**What it is**: the Pydantic models (`UiConfig`, `ApiEndpointConfig`, `DatabaseConfig`,
`ClickHouseConfig`, `BrowserConfig`, `AuthConfig`, `FeatureFlags`, `EnvironmentSettings`) that every
`config/environments/*.yaml` file is validated against.

**When to change it**: only when a `config/environments/*.yaml` block needs a field that doesn't
exist yet on any model — e.g. adding `protocol` to `ClickHouseConfig` when ClickHouse support was
first introduced.

**Who changes it**: **Framework Maintainer**. This is shared schema — a mistake here breaks
`get_settings()` for every environment, every test, at once. New fields should have safe defaults so
existing YAML files keep validating unchanged.

**Example** (real, from this repo's history):
```python
class ClickHouseConfig(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = 8123
    database: str = ""
    username: str = ""
    password: str = ""
    protocol: str = "http"  # http | https
    timeout_seconds: int = 30
```

---

## 5. Dashboard / ClickHouse query configuration — `config/dashboards/*.json`

**What it is**: real ClickHouse query catalogs for dashboard-style validation (widget queries +
export-validation total/per-row queries), loaded via `framework.models.DashboardConfig.load(name)`
and executed via `framework.database.clickhouse.DashboardRepository`. See
`config/dashboards/sample_dashboard.json` for the working example (1 export validation, 1 widget) —
a small, non-proprietary illustration of the shape; a real integration typically has many more
widgets/exports.

**When to change it**: when you have a **real, confirmed** ClickHouse query for a new dashboard or
a new metric on an existing one — table/column names verified against the actual schema, ideally
with a comment explaining how it was confirmed (a HAR capture, a DBA-provided query, etc.).

**Who changes it**: **Automation Engineer**, but only with real evidence. This framework's standing
rule: **no placeholder SQL without database evidence**. A query template you're not sure is correct
doesn't belong here — flag it and leave the corresponding `framework.database.clickhouse` repository
method raising `NotImplementedError` instead until real evidence exists.

**Example** (real entry from `sample_dashboard.json`):
```json
"totalUsage": {
  "description": "Total usage volume for the selected date range/host.",
  "tolerancePct": 2.0,
  "totalTemplate": "SELECT sum(usage_units) AS total FROM {{CH_DATABASE}}.daily_usage_summary WHERE host_id IN ({{HOST_ID}}) AND event_date BETWEEN {{DATE_FROM_UNIX}} AND {{DATE_TO_UNIX}}",
  "perRowTemplate": "..."
}
```
`{{CH_DATABASE}}`, `{{HOST_ID}}`, `{{DATE_FROM_UNIX}}`, `{{DATE_TO_UNIX}}` are filled in at runtime by
`DashboardRepository._fill_template()` — never hardcode a real database name or host id into
the template itself.

**New dashboard file naming**: `config/dashboards/{dashboard_id}.json`, where `dashboard_id` matches
the `dashboardId` field inside the file — `DashboardConfig.load("sample_dashboard")` looks up
`sample_dashboard.json` by that exact name.

---

## 6. Framework constants — `framework/constants/timeouts.py`

**What it is**: the single source of truth for default timeouts and retry behavior used across the
whole framework (`Timeouts.DEFAULT_ACTION_TIMEOUT_MS`, `Timeouts.RETRY_MAX_ATTEMPTS`, etc.) — used
by `BasePage`, `WaitManager`, `framework.retry.retry_on`, the ClickHouse layer, and more.

**When to change it**: when a default is wrong for the *whole framework* — e.g. every environment's
navigation is consistently timing out at 30s and needs 45s as the new baseline. **Not** the place
for a one-off "this specific page is slow" fix — use the `timeout_ms` parameter most `BasePage`
methods already accept for that.

**Who changes it**: **Framework Maintainer**. A change here affects every test in every module.

**Example** (current values):
```python
class Timeouts:
    DEFAULT_ACTION_TIMEOUT_MS = 15_000
    DEFAULT_NAVIGATION_TIMEOUT_MS = 30_000
    SHORT_WAIT_MS = 5_000
    LONG_WAIT_MS = 60_000

    RETRY_MAX_ATTEMPTS = 3
    RETRY_WAIT_MULTIPLIER_SECONDS = 1
    RETRY_WAIT_MAX_SECONDS = 10
```
Per-environment timeout overrides (which don't touch this file at all) already exist via
`AUTOMATION_ACTION_TIMEOUT_MS` / `AUTOMATION_NAVIGATION_TIMEOUT_MS` in `.env.{environment}` — reach for that first.

---

## 7. Pytest configuration & markers — `pyproject.toml` → `[tool.pytest.ini_options]`

**What it is**: pytest's own config — `testpaths`, strict-marker enforcement, and the full list of
registered markers. `--strict-markers` means **an unregistered marker fails the test run** — this
is deliberate, so a typo'd `@pytest.mark.smoke_` doesn't silently vanish from a filtered run.

**When to change it**:
- **Add a marker** when you're building out a new business module or test category (this repo
  already has one per module: `subscriber_management`, `sim_management`, `provisioning`, `billing`,
  plus cross-cutting ones like `smoke`, `regression`, `hybrid`, `database`).
- **Change `testpaths`/`addopts`** only when the overall test-discovery strategy changes.

**Who changes it**:
- **Automation Engineer** adds a marker for their own new module.
- **Framework Maintainer** changes `addopts`, `testpaths`, or removes/renames an existing marker
  (renaming breaks every test file that uses the old name).

**Example** (real, from this repo):
```toml
markers = [
  "smoke: fast critical-path checks",
  "database: database validation tests",
  "auth: authentication state management (.auth/*.json save/restore/reuse) tests",
  "subscriber_management: Subscriber Management module",
  "sim_management: SIM Management module",
]
```
To add your own module's marker, append one line here, then use `pytestmark = pytest.mark.<name>`
at the top of your test file — same convention every existing module follows.

---

## 8. Dependencies — `pyproject.toml` → `[tool.poetry.dependencies]`

**What it is**: the framework's runtime and dev dependency versions, managed by Poetry
(`poetry.lock` is the resolved, committed lockfile — always regenerate it with `poetry lock
--no-update` after editing this section, never hand-edit the lockfile).

**When to change it**: adding a new library the framework genuinely needs (e.g. `clickhouse-connect`
was added when the ClickHouse layer was built), or bumping a version for a security fix.

**Who changes it**: **Framework Maintainer**. A new dependency affects every environment (local,
CI, Docker) and needs `poetry.lock` regenerated + committed alongside it. If you're an automation
engineer and your test needs a new library, ask a maintainer to add it rather than installing it
ad hoc into your local `.venv` — the CI/Docker builds only see what's declared here.

**Example** (real addition from this repo's history):
```toml
[tool.poetry.dependencies]
clickhouse-connect = "^0.7.0"
```
followed by `poetry lock --no-update` to update `poetry.lock` to match.

**Optional dependency groups** (`oracle`, `mssql`) are separate — only install them with
`poetry install --with oracle` when you actually need Oracle/SQL Server drivers; they're not part
of the default install.

---

## 9. Code-quality tooling

### 9.1 `pyproject.toml` → `[tool.black]` / `[tool.ruff]` / `[tool.mypy]` / `[tool.bandit]`

**What it is**: the exact rules every commit is held to — line length (100), Python target
(3.13), ruff's enabled rule sets, mypy's strict mode, bandit's excluded directories.

**When to change it**: rarely, and only with team agreement — this changes what "passing lint"
means for everyone, retroactively flagging (or silencing) things across the whole codebase.

**Who changes it**: **Framework Maintainer** only.

**Example** (current, real):
```toml
[tool.mypy]
python_version = "3.13"
strict = true
exclude = ["reports/", "artifacts/", "logs/"]

[tool.bandit]
exclude_dirs = ["tests", "reports", "artifacts", ".venv"]
```

### 9.2 `.pre-commit-config.yaml`

**What it is**: the hooks that run automatically before each commit — trailing whitespace, YAML/TOML
validation, black, ruff (with `--fix`), mypy (scoped to `framework/`), bandit (scoped to
`framework/`).

**When to change it**: when a hook's pinned version needs bumping (keep it in sync with the matching
tool version in `pyproject.toml`), or a new hook is genuinely needed.

**Who changes it**: **Framework Maintainer**.

**Example** (real, note the `files:` scoping):
```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.11.2
  hooks:
    - id: mypy
      args: ["--config-file=pyproject.toml"]
      files: ^framework/
```
`mypy`/`bandit` are intentionally scoped to `framework/`, not `tests/` — see the note in §12 for why
(`allure.feature`/`allure.story` decorators have no type stubs, so `tests/` isn't held to the same
mypy bar; this is a known, accepted gap, not an oversight).

---

## 10. CI/CD pipeline — `.github/workflows/ci.yml`

**What it is**: the full CI definition — a `lint` job (black/ruff/mypy/bandit), a `test` job matrixed
over suites (`smoke`, `negative`, `accessibility`, `visual`, `e2e`), separate `test-api`,
`test-database` (matrixed over sqlite/postgresql/mysql), `test-hybrid`, `test-testdata` jobs, a
report-aggregation job, and a `docker` build-and-smoke-test job.

**When to change it**:
- **Add a new suite to the `test` job's matrix** when a new top-level `tests/<suite>/` directory
  with its own pytest marker is created (the comment in the workflow explains why: an empty suite
  makes pytest exit 5 and fail the job, so only list suites that actually have tests).
- **Add a new dedicated job** (mirroring `test-testdata`/`test-hybrid`) when a module's tests need
  their own environment setup (a new service container, a different Playwright browser set, etc.).

**Who changes it**: **Framework Maintainer**. This is the gate everyone's PR goes through — a
mistake here blocks the whole team, not just one engineer.

**Example** (the actual matrix, real):
```yaml
strategy:
  fail-fast: false
  matrix:
    # Add suites here as they're built out (sanity, regression, ...).
    # An empty suite makes pytest exit 5 ("no tests collected") and fail
    # the job, so only list suites that actually have tests today.
    suite: [smoke, negative, accessibility, visual, e2e]
```

---

## 11. Docker & local services

### 11.1 `docker-compose.yml`

**What it is**: local service definitions — the framework's own image (`automation`, `api-tests`,
`database-tests`, `hybrid-tests` services, each running a different suite), plus real
Postgres/MySQL/Oracle-XE containers so `tests/database` can run against a real server instead of
SQLite, purely via env vars (no test-code change — see the comment block above the `postgres:`
service for why credentials there are fixed, not `${AUTOMATION_DB_*:-...}`-templated).

**When to change it**: adding a new local service (a new database, a new dependent service), or a
new "run this suite in a container" entry.

**Who changes it**: **Framework Maintainer**.

**Example** (how to point the real test suite at a real Postgres, zero code changes):
```bash
docker compose up -d postgres
AUTOMATION_DB_DIALECT=postgresql AUTOMATION_DB_HOST=localhost AUTOMATION_DB_PORT=5432 \
  AUTOMATION_DB_NAME=sample_app AUTOMATION_DB_USER=automation_qa AUTOMATION_DB_PASSWORD=automation_qa_password \
  poetry run pytest tests/database
```

### 11.2 `docker/Dockerfile`

**What it is**: the runtime image build — Python 3.13-slim base, Poetry install, Playwright browser
install (`--with-deps`, since the slim base has none of the OS packages each browser needs), then
the app code copied in.

**When to change it**: bumping the Python/base-image version, adding an OS-level dependency a new
library needs, or changing which Playwright browsers get installed.

**Who changes it**: **Framework Maintainer**.

---

## 12. Test fixture registration — `tests/conftest.py`

**What it is**: the top-level list of fixture plugin modules pytest loads for every test —
`framework.fixtures.driver_fixtures`, `framework.fixtures.auth_fixtures`,
`framework.api.fixtures.api_fixtures`, `framework.database.fixtures.database_fixtures`,
`framework.hybrid.fixtures`, `framework.testdata.fixtures.testdata_fixtures`.

**When to change it**: only when an entirely new *fixture layer* is added (like when
`framework.fixtures.auth_fixtures` was introduced for `.auth/*.json` reuse) — not for adding a new
fixture *inside* an existing module, which just works once that module's plugin is already
registered.

**Who changes it**: **Framework Maintainer**.

**Example** (the real, current list):
```python
pytest_plugins = [
    "framework.fixtures.driver_fixtures",
    "framework.fixtures.auth_fixtures",
    "framework.api.fixtures.api_fixtures",
    "framework.database.fixtures.database_fixtures",
    "framework.hybrid.fixtures",
    "framework.testdata.fixtures.testdata_fixtures",
]
```

---

## 13. Common recipes

A few frequent changes, mapped to exactly which file(s) they touch:

**"I need to add a new environment (e.g. `staging`)."**
→ `config/environments/staging.yaml` (Framework Maintainer creates it, modeled on `qa.yaml`) +
`.env.staging.example` (Automation Engineer fills in real values locally as `.env.staging`) +
add `staging` to `framework/enums/environment.py`'s `Environment` enum (Framework Maintainer).

**"I need my test to hit a new internal API."**
→ Add a block under `api:` in the relevant `config/environments/*.yaml` (Automation Engineer, using
the existing `ApiEndpointConfig` schema) + the matching `AUTOMATION_API_*` vars in `.env.example`.

**"My module's tests need their own pytest marker."**
→ One line in `pyproject.toml`'s `markers = [...]` list (Automation Engineer).

**"A specific page is slow and keeps timing out."**
→ Pass `timeout_ms=` to the specific `BasePage` call (per-call override) — do **not** change
`framework/constants/timeouts.py`, which is global.

**"I have a real ClickHouse query for a new dashboard widget."**
→ Add the entry to the relevant `config/dashboards/*.json` file's `widgets` array (Automation
Engineer, only with a confirmed real query — see §5).

**"CI needs to run my new test suite."**
→ Add the suite name to the `matrix.suite` list in `.github/workflows/ci.yml` (Framework Maintainer)
— only after the suite directory has real, passing tests in it.

---

## 14. Safety rules (apply everywhere in this guide)

- **A real secret, hostname, or credential never goes into a tracked file.** `.env`,
  `.env.{environment}`, and `.auth/*.json` are all gitignored for this reason — `config/environments/*.yaml`
  and `config/dashboards/*.json` are tracked and must only ever contain `${VAR:-}` placeholders or
  genuinely non-sensitive literals (timeouts, booleans, public URLs).
- **`poetry.lock` is committed and machine-generated.** Never hand-edit it; always regenerate with
  `poetry lock --no-update` after a `pyproject.toml` dependency change, and commit both together.
- **A schema change (`framework/config/models.py`) must keep existing YAML valid.** New fields need
  safe defaults — a maintainer adding a required field with no default breaks every environment's
  config load at once.
- **No placeholder SQL, no guessed locators.** This framework's standing development policy is
  evidence-driven: a `config/dashboards/*.json` query or a Page Object locator only gets added once
  there's a real, confirmed source (a working query, a Playwright codegen recording) — never
  invented to "fill a gap."

---

## 15. Keeping this guide current

This document is only useful if it matches reality. When you add a genuinely new *kind* of
configurable file (not just a new entry in an existing one), add a section here in the same
Framework Maintainer PR — treat an out-of-date maintenance guide the same as a failing test.
