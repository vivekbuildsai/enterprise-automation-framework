# Enterprise Automation Framework

A generic, product-agnostic Python test automation framework — UI (Playwright),
API, and database validation on one core, built so it can be cloned and
customized for any application or customer rather than rebuilt from scratch.
Nothing in `framework/` assumes a specific company, product, or domain; the
sample pages/schemas/data shipped with it exist only to prove every layer
works end to end.

## What this is

A **Clean Architecture** automation platform where today's UI automation and
tomorrow's API/database/performance/security/AI-assisted testing plug into
the same core without rewrites. It's built around one reusable validation
pattern — capture what the UI/API produced, reproduce the same number from
the database, compare within a tolerance, report the result — generalized so
it isn't tied to one backend, one database engine, or one application.

## The product in one minute

Five capabilities. The first two are always on; the last three are
independently optional (off by default — see
[Modular capabilities](#modular-capabilities)):

| Capability | What it does | Optional? |
|---|---|---|
| **Core Automation** | Playwright UI + REST API clients, Page Objects/Components, Allure/HTML reporting | No |
| **Data Validation** | Network/JSON-RPC capture → extraction → database comparison, with real numeric tolerance (`DataComparator` + `Tolerance`) | No |
| **Application Discovery** | Evidence-only UI/API/DB introspection + code scaffolding (`framework.discovery`) | Yes |
| **Framework Sync** | Read-only analysis + migration scaffolding for an *existing* automation repo (`framework.sync`) | Yes |
| **AI Assistance** | Optional, provider-agnostic recommendation layer over Discovery/Sync output (`framework.ai`) | Yes |

Five runnable examples cover all five — see [`examples/`](examples/) and
run them yourself: `poetry run pytest examples/ -v`.

## Key capabilities

- **UI automation** on Playwright (Chromium/Firefox/WebKit), Page Object +
  Page Component Model, no hardcoded waits, testid > role > label > css > xpath
  locator priority.
- **API automation**: pluggable auth (Bearer/JWT/Basic/API Key/Cookie/OAuth2),
  fluent request/response builders, JSON Schema validation.
- **Database validation**: one dialect-agnostic layer supporting SQLite,
  PostgreSQL, MySQL, Oracle, and SQL Server — switching databases is a
  configuration change, not a code change.
- **ClickHouse-backed dashboard/widget validation**: capture a UI widget's
  network response, reproduce it from ClickHouse, compare with a configurable
  tolerance — see [Validation flow](#validation-flow) below.
- **Generic network/JSON-RPC interception**: `NetworkInterceptor` captures
  matching requests/responses from a real Playwright page; `WidgetDataExtractor`
  turns a match into the same row shape a database query produces.
- **Reusable validation engine**: exact, numeric, percentage/absolute
  tolerance, null-safe, type/string/date normalization, row- and
  field-level comparison.
- **Test Data Management**: builders, factories, scenario library, seeding
  and cleanup, PII masking, synthetic data generation.
- **Allure + HTML reporting**, screenshots/traces/video on failure,
  structured logging.
- **Docker + CI/CD ready**: one Dockerfile, a `docker-compose.yml` with real
  Postgres/MySQL/Oracle service containers, a GitHub Actions pipeline that
  matrixes the database suite across dialects.
- **Optional, independently-enabled capabilities** (off by default; core
  automation runs identically with all of them disabled): **Application
  Discovery** (`framework.discovery` — evidence-only UI/API/DB
  introspection + code scaffolding), **Existing Framework Sync**
  (`framework.sync` — read-only analysis and migration scaffolding for an
  existing automation repo), **AI Assistance** (`framework.ai` — pluggable,
  provider-agnostic, disabled by default). See
  [Modular capabilities](#modular-capabilities) below.

## Modular capabilities

This framework is a set of independent capabilities, not one monolithic
system — see [docs/ModularArchitecture.md](docs/ModularArchitecture.md)
for the full capability matrix, feature-combination examples, and the
"core never imports an optional package" rule that makes this true by
construction, not just by convention. Optional capabilities:

| Capability | Package | Feature flag | Doc |
|---|---|---|---|
| Application Discovery | `framework.discovery` | `discovery` | [docs/ModularArchitecture.md](docs/ModularArchitecture.md#application-discovery-frameworkdiscovery) |
| Existing Framework Sync | `framework.sync` | `framework_sync` | [docs/FrameworkSync.md](docs/FrameworkSync.md) |
| AI Assistance | `framework.ai` | `ai_assistance` | [docs/ModularArchitecture.md](docs/ModularArchitecture.md#ai-assistance-frameworkai) |

None of these are required for core UI/API/database automation to work,
and none require each other — enable any subset independently via
`feature_flags` in `config/environments/*.yaml`.

**One CLI for all of it** — `python -m framework <command>` dispatches to
each capability's own independently-runnable CLI:

```bash
poetry run python -m framework discover ui <url> --report report.json
poetry run python -m framework discover recommend --report report.json  # optional AI layer
poetry run python -m framework sync analyze <source> --report analysis.json
poetry run python -m framework sync recommend --report analysis.json    # optional AI layer
poetry run python -m framework sync scaffold --report analysis.json
poetry run python -m framework validate --expected e.json --actual a.json
poetry run python -m framework report generate
```

See [docs/ModularArchitecture.md](docs/ModularArchitecture.md) for the
full CLI reference and the AI-assisted recommendation pipeline
(`Discovery/Sync → AI Provider → Recommendation → RecommendationConfidence
→ Human Review`).

## Architecture

```
                      TESTS
                        │
                        ▼
                 PAGE / COMPONENT
                        │
                        ▼
                   PLAYWRIGHT
                        │
                ┌───────┴────────┐
                ▼                ▼
             UI DATA         NETWORK DATA
                                 │
                                 ▼
                       JSON / JSON-RPC
                     (NetworkInterceptor)
                                 │
                                 ▼
                       DATA EXTRACTOR
                     (WidgetDataExtractor)
                                 │
                ┌────────────────┴────────────────┐
                ▼                                  ▼
           DATABASE                          API / SERVICE
     (SQLite/Postgres/MySQL/                 (framework/api —
      Oracle/SQL Server,                      ApiClient, auth
      ClickHouse via                          strategies,
      DashboardRepository)                    ResponseValidator)
                │                                  │
                └────────────────┬─────────────────┘
                                  ▼
                          NORMALIZATION
                                  │
                                  ▼
                         VALIDATION ENGINE
                        (DataComparator,
                         ClickHouseValidator)
                                  │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                   TOLERANCE          BUSINESS RULES
                  (tolerance_pct)    (testdata.validators)
                        │                   │
                        └─────────┬─────────┘
                                  ▼
                             ASSERTIONS
                          (Assert, UIAssert,
                            SoftAssert)
                                  │
                                  ▼
                          ALLURE / HTML
                                  │
                                  ▼
                        EVIDENCE & REPORTS
                     (screenshots, traces,
                      SQL/timing telemetry)
```

Page Objects and Components own selectors and expose business actions only
(`login_page.login(user, pass)`, never `page.click("#btn")`). Services
orchestrate Page Objects, repositories, and validators so a test reads as a
sequence of business steps, not a sequence of Playwright calls.

## Validation flow

The framework's core validation idea, generalized from a widget/dashboard
pattern into something any application can use:

```
Test Scenario
      │
      ▼
Page / Component (drives the UI)
      │
      ▼
Playwright Interaction
      │
      ▼
Network / JSON-RPC Interceptor  (framework.network.NetworkInterceptor /
      │                          JsonRpcInterceptor — captures the real
      │                          request/response while the UI acts)
      ▼
Response / Widget Data Extractor  (framework.network.WidgetDataExtractor —
      │                            matches by a configurable `identify` rule,
      │                            extracts dimension/metric rows)
      ▼
Data Normalizer  (framework.database.utilities.comparison — type/string/
      │           date normalization, so "1002" == 1002 == " 1002 ")
      ▼
Database / ClickHouse Service  (framework.database.clickhouse.DashboardRepository
      │                         reproduces the same number from the DB)
      ▼
Validation Engine  (DataComparator / ClickHouseValidator)
      │
      ▼
Tolerance / Business Rules  (percentage or absolute tolerance, e.g.
      │                      expected=1000, actual=1002, tolerance=±5 → PASS)
      ▼
Assertion
      │
      ▼
Evidence  (screenshot, trace, SQL text, comparison diff)
      │
      ▼
Allure / HTML Report
```

Nothing here assumes JSON-RPC specifically, or ClickHouse specifically:
`NetworkInterceptor` is the generic base (any REST/GraphQL/JSON-RPC
endpoint), `JsonRpcInterceptor` is one specialization, and the database
half is written against an interface pattern so PostgreSQL/MySQL/SQL Server
clients can sit next to `ClickHouseClient` without touching this pipeline.

This whole pipeline, executed end to end against real (mocked-transport)
framework code, is [`examples/data_validation`](examples/data_validation)
— the framework's key differentiator and the best starting point for
understanding what this product actually does.

## Project structure

```
framework/
├── pages/            Page Object Model — one class per screen
├── components/       Page Component Model — 14 reusable widgets
├── network/           NetworkInterceptor, JsonRpcInterceptor, WidgetDataExtractor
├── api/                API automation: client, auth, builders, validators
├── database/           Dialect-agnostic DB layer (SQLAlchemy) + clickhouse/
│   └── clickhouse/       ClickHouseClient, DashboardRepository, ClickHouseValidator
├── models/             Domain models + DashboardConfig (widget/tolerance config)
├── services/           Business-level orchestration over pages/repositories
├── testdata/            Builders, factories, scenarios, seeding, masking
├── config/               EnvironmentSettings — layered .env + YAML config
├── validators/ assertions/  Reusable comparison/assertion layers
└── hybrid/                 ValidationFacade — dispatches UI/API/DB checks
                             by validation_mode, zero test-code changes

tests/                 smoke/ regression/ e2e/ api/ database/ network/ ...
config/environments/   dev/qa/uat/preprod/production YAML
config/dashboards/     Sample widget/tolerance configs (JSON)
docs/                  Architecture, database, testdata, and API deep-dives
```

## Installation

```bash
poetry install --no-root
poetry run python -m playwright install chromium firefox webkit
cp .env.example .env
```

## Configuration

Layered, environment-variable-driven, never hardcoded:

```
.env  →  .env.{environment}  →  real process/CI environment variables
(shared defaults)  (per-env override)   (highest precedence)
```

`config/environments/{dev,qa,uat,preprod,production}.yaml` define the shape
(`ui`, `ui_targets`, `api`, `database`, `clickhouse`, `browser`, `auth`,
`feature_flags`); every value is `${AUTOMATION_VAR:-default}` so nothing
secret is ever committed. See [docs/GettingStarted.md](docs/GettingStarted.md)
and [docs/DatabaseConfiguration.md](docs/DatabaseConfiguration.md).

## Running tests

```bash
poetry run pytest tests/smoke tests/negative tests/accessibility tests/visual tests/e2e -v  # UI
poetry run pytest tests/api -v --alluredir=reports/allure-results                            # API
poetry run pytest tests/database -m "database and not integration" -v                        # Database (SQLite, zero setup)
poetry run pytest tests/database/integration -m hybrid -v                                    # Hybrid (UI+API+DB)
poetry run pytest tests/network -v                                                            # Network/widget interception
poetry run pytest tests/testdata -v                                                           # Test Data Management
```

## Docker execution

```bash
docker build -f docker/Dockerfile -t enterprise-automation-framework:local .
docker compose up -d postgres mysql   # optional: real DB backends
docker compose run --rm automation
```

`docker-compose.yml` also defines `api-tests`, `database-tests`,
`hybrid-tests`, and an `allure-report` service (Allure Docker service on
`:5050`).

## Allure reporting

Every suite writes to `reports/allure-results`; generate/serve locally with
`allure serve reports/allure-results`, or use the `allure-report` Docker
service / the CI `report` job. Failed database validations attach the SQL
text, elapsed time, row count, and comparison diff automatically (see
`framework.database.telemetry`).

## Database validation

`framework.database` is dialect-agnostic (SQLite/PostgreSQL/MySQL/Oracle/SQL
Server via one `ConnectionFactory`), with a Repository pattern and
`DataComparator` for DB-vs-Expected/API/UI comparison.
`framework.database.clickhouse` is a parallel, ClickHouse-specific layer
(`ClickHouseClient`, `ClickHouseQueryExecutor`, `BaseClickHouseRepository`,
`ClickHouseValidator`) for the widget-validation pipeline above — ClickHouse
is the first concrete implementation, not a hard dependency; a
PostgreSQL/MySQL client can be added beside it without changing
`DataComparator` or the validation engine. See
[docs/DatabaseFramework.md](docs/DatabaseFramework.md).

## JSON-RPC / network interception

`framework.network.NetworkInterceptor` attaches to a real Playwright `Page`
and records every response matching a URL pattern, parsing JSON bodies
where possible — no assumption about REST vs. JSON-RPC vs. any specific
endpoint shape. `JsonRpcInterceptor` adds `calls_named(method)` for
JSON-RPC-flavored APIs (single endpoint, `{"method": ..., "params": ...}`
body). Both are verified in `tests/network/unit/test_network_interception.py`
against a real local Playwright page with a mocked route — proof the
plumbing works independent of any live application.

## Widget validation

`config/dashboards/*.json` (loaded via `framework.models.DashboardConfig`)
declares, per widget: how to identify it in a captured request
(`must_have`/`must_not_have`/`skip_if_request_contains`), which fields to
extract (`dimension`/`metric`), and the ClickHouse query template that
should reproduce the same numbers. `WidgetDataExtractor.find_matching()` +
`.extract_rows()` turn a captured exchange into rows;
`DashboardRepository.run_widget_query()` reproduces the same rows from
ClickHouse; `DataComparator`/`ClickHouseValidator` compare them (see
[Tolerance-based validation](#tolerance-based-validation) below for
exactly what "compare" means today).
`config/dashboards/sample_dashboard.json` is a small, non-proprietary
example — swap in your own application's real widget configs the same way.

## Tolerance-based validation

`framework.database.utilities.comparison.DataComparator.compare()` supports
exact (case/whitespace-normalized) comparison and, given a `Tolerance`,
real numeric percentage and/or absolute tolerance comparison — implemented,
not aspirational:

```python
from framework.database.utilities import DataComparator, Tolerance

result = DataComparator.compare(
    {"total": 1000}, {"total": 1005},
    left_label="Expected", right_label="Actual",
    tolerance=Tolerance(percentage=1.0),
)
assert result.matched  # 0.5% difference, within ±1%
print(result.to_report())
```

`Tolerance(percentage=..., absolute=...)` — either or both; when both are
given, a field passes if it satisfies *either* one. Handles integers,
floats, negative values, and a zero expected value (a percentage tolerance
alone requires an exact match against zero; pair it with `absolute=` for a
real margin). `None`/`None` always matches; one `None` and one real value
never does, regardless of tolerance. Every compared field is exposed as a
`FieldComparison` (`result.field_comparisons`) — `expected`, `actual`,
`difference`, `difference_pct`, `tolerance`, `comparison_type`, `matched`,
and a ready-to-read `message` — not just the fields that failed.
`DashboardConfig`/`WidgetConfig`/`ExportValidationConfig`'s `tolerance_pct`
values are meant to be passed straight into `Tolerance(percentage=...)` by
whatever validator wires a widget check together (see
[examples/data_validation](examples/data_validation) for a full worked
example). Tolerance logic lives entirely in this one reusable comparator —
never hardcoded inside a test.

## Extending the framework

1. **New target application**: add a `ui_targets.<name>` entry in
   `config/environments/*.yaml`, point real credentials at `.env.dev`
   (never commit them), record real Playwright codegen, build Page
   Objects/Components only against confirmed evidence.
2. **New database backend**: implement a client alongside
   `ClickHouseClient` (or extend `framework.database.drivers.dialect_registry`
   for a new SQLAlchemy dialect) — `DataComparator` and the validation
   engine don't change.
3. **New widget/dashboard**: add a `config/dashboards/<name>.json` following
   `sample_dashboard.json`'s shape; no code changes needed.
4. **New domain model**: add a dataclass under `framework/models/` or
   `framework/database/models/`; it plugs into `BaseClickHouseRepository`/
   `ValidationService` without special-casing (see `Brand` for the minimal
   example).

See [docs/Architecture.md](docs/Architecture.md),
[docs/FolderStructure.md](docs/FolderStructure.md), and
[FRAMEWORK_MAINTENANCE_GUIDE.md](FRAMEWORK_MAINTENANCE_GUIDE.md) (the
operational manual: every configurable file, when to change it, who
changes it).

## CI/CD usage

GitHub Actions (`.github/workflows/ci.yml`): lint (Black/Ruff/MyPy/Bandit) →
UI/API/database/hybrid/testdata suites in parallel jobs → Allure report
aggregation → Docker image build + smoke verification, gated on `main`. The
database job matrixes SQLite/PostgreSQL/MySQL with real service containers.
Any CI system that can run `poetry install && poetry run pytest` and spin up
Postgres/MySQL containers can reproduce this pipeline.

## Example workflow

Five small, **executable** examples live in [`examples/`](examples/) — real
framework APIs, not illustrative pseudocode. Run all of them:

```bash
poetry run pytest examples/ -v
```

The end-to-end pipeline this framework is built around — UI → network →
data extraction → database → tolerance validation → report — is
[`examples/data_validation/test_widget_vs_database_example.py`](examples/data_validation/test_widget_vs_database_example.py):

```python
with NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
    page.evaluate("() => fetch('https://example.test/api/dashboard', {...})")

exchange = WidgetDataExtractor.find_matching(widget.identify, interceptor.captured)
ui_row = WidgetDataExtractor.extract_rows(exchange, widget.extractors)[0]

db_row = dashboard_repository.run_widget_query(dashboard_config, widget_id, ...)[0]

result = DataComparator.compare(
    {"total": db_row["total"]}, {"total": ui_row["usage_units"]},
    left_label="Database", right_label="UI Widget",
    tolerance=Tolerance(percentage=widget.tolerance_pct),
)
assert result.matched, result.to_report()
```

See [`examples/README.md`](examples/README.md) for what each of the five
examples demonstrates (UI automation, this UI+data-validation pipeline,
Framework Sync, Application Discovery, and optional AI).

## Future extension possibilities

- Additional database clients (PostgreSQL/MySQL) alongside `ClickHouseClient`
  for the widget-validation pipeline.
- `framework/performance`, `framework/security` packages (directories exist,
  implementation pending real requirements).
- `framework.ai`: self-healing locator fallback and LLM-assisted failure
  root-cause summaries, built on the same `AIProvider` abstraction already
  wired into Discovery/Sync's recommendation pipelines — these two
  specific use cases just aren't implemented yet.
- `framework.sync` Mode 3 (MIGRATE) and Mode 4 (SYNC) — genuine
  source-to-source migration and diff-driven re-synchronization,
  intentionally not implemented yet (see
  [docs/FrameworkSync.md](docs/FrameworkSync.md)).
- SOAP/GraphQL/gRPC/WebSocket client scaffolds alongside `framework/api`.

See [docs/FutureRoadmap.md](docs/FutureRoadmap.md) for the full,
milestone-by-milestone history and roadmap.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
