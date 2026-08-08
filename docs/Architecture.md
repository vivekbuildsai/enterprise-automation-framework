# Architecture

## Layering

```
tests/                  <- what to verify (business intent, one assertion style: Assert/SoftAssert)
  smoke/ sanity/ regression/ e2e/ api/ backend/ database/ performance/ security/

framework/pages/         <- Page Object Model: one class per screen (+ one subpackage per module)
framework/components/    <- Page Component Model: 14 reusable widgets shared across pages
framework/navigation/    <- AppNavigator: composes Sidebar/TopNav/Breadcrumb into "go to module X"
framework/workflows/     <- Multi-page business flows (LoginWorkflow, SubscriberSearchWorkflow, ...)
framework/waits/         <- WaitManager: every non-trivial wait condition, no hardcoded sleeps
framework/locators/      <- Locators: centralized locator-priority strategy (testid > role > label > css > xpath)
framework/accessibility/ <- AccessibilityChecker (axe-core) — critical/serious violations fail the run
framework/visual/        <- VisualComparator — screenshot-diff visual regression testing
framework/services/      <- (reserved) backend-layer clients — API moved into framework/api/, DB into framework/database/, see below
framework/drivers/       <- Browser lifecycle (Factory Pattern: BrowserFactory, DriverManager)
framework/api/           <- API automation module (implemented — see below)
framework/database/      <- Database validation module (implemented — see below)
framework/hybrid/        <- ValidationFacade + fixtures: UI/API/DB dispatch by ValidationMode (implemented)
framework/testdata/      <- Test Data Management platform: builders/factories/scenarios/datasets/seed/cleanup (implemented — see below)
framework/fixtures/      <- pytest wiring between config, drivers, and tests
framework/core/          <- BaseTest and other cross-cutting test-level scaffolding
framework/config/        <- environment settings (Pydantic Settings, Builder-style loader)
framework/assertions/    <- Assert (hard) / SoftAssert (multi-failure) / UIAssert (element-level)
framework/exceptions/    <- one exception hierarchy for the whole framework
framework/retry/         <- @retry_on decorator (Tenacity-backed)
framework/logger/        <- structured logging (Loguru), one bound logger per component
framework/validators/    <- schema/business-rule validators (JSON Schema, DB result shape, etc.)
framework/ai/            <- optional AI provider abstraction (implemented — pluggable AIProvider,
                             redaction, Discovery/Sync recommendation pipelines; self-healing
                             locators/RCA/visual-diff are future extensions, not built — see
                             docs/FutureRoadmap.md)
framework/security/      <- (reserved) security test helpers (auth, injection, header checks)
framework/performance/   <- (reserved) performance test helpers (load shaping, timing assertions)
framework/telemetry/     <- execution metrics (timings, retry counts, environment facts)
framework/integrations/  <- (reserved) outbound integrations (Slack/Jira/etc. notification, future)
framework/models/        <- shared Pydantic domain models (Brand, DashboardConfig, ...) — the
                             Subscriber/Tenant domain models live in framework/database/models/
framework/utilities/     <- screenshots, files, dates, random data, JSON/CSV/Excel test-data loader
framework/enums/         <- Environment, BrowserType, ValidationMode, ...
framework/constants/     <- Timeouts and other fixed values
```

Every layer above only depends on layers below it. `tests/` never imports
Playwright directly — it goes through `framework/pages` and `framework/services`.
`framework/pages` never imports a database driver. This is what "Clean
Architecture" buys us here: the UI can be swapped, the DB can be swapped, and
tests don't notice.

## framework/api/ — the API automation module

A self-contained sibling to the UI stack, not a dependency of it (and not
depended on by it) — `tests/api/` works with zero Playwright installed:

```
framework/api/client/       ApiClient — GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS over httpx
framework/api/auth/         Pluggable httpx.Auth strategies (Bearer/JWT/Basic/API Key/Cookie/OAuth2 x2)
framework/api/builders/     RequestBuilder (fluent) -> RequestSpec
framework/api/validators/   ResponseValidator (fluent) + JSON path resolver
framework/api/schemas/      *.json JSON Schema files + registry (jsonschema/referencing)
framework/api/endpoints/    Endpoints — centralized path templates
framework/api/models/       Pydantic request/response models
framework/api/services/     AuthService/UserService (domain facades), ApiValidator (hybrid-validation-ready)
framework/api/middleware/   httpx event hooks: correlation ID, structured logging, Allure attachment
framework/api/fixtures/     pytest fixtures: settings -> ApiClient -> services
```

Full detail: [APIFramework.md](APIFramework.md), [Authentication.md](Authentication.md),
[RequestBuilder.md](RequestBuilder.md), [Validators.md](Validators.md), [Schemas.md](Schemas.md).

## framework/database/ — the database validation module

A third sibling to the UI and API stacks — supports Oracle, PostgreSQL,
MySQL, SQL Server, and SQLite through one dialect-agnostic code path;
switching between them is a `config/environments/<env>.yaml` change, never
a code change:

```
framework/database/connection/     ConnectionFactory, ConnectionPoolManager, DatabaseManager
framework/database/drivers/        dialect_registry — DbDialect -> SQLAlchemy driver/port/pip-package
framework/database/queries/        raw SQL by domain — the only place SQL text lives
framework/database/models/         frozen dataclasses, one per domain
framework/database/repositories/   BaseRepository + 7 domain repositories (Repository pattern)
framework/database/services/       UnitOfWork, SeedManager
framework/database/validators/     DatabaseValidator + 6 domain validators (DB vs Expected/API/UI)
framework/database/utilities/      QueryExecutor, TransactionManager, ResultMapper, DataComparator,
                                    SchemaManager, CleanupManager, CredentialResolver
framework/database/fixtures/       pytest fixtures wiring all of the above
framework/database/telemetry/      Allure attachment helpers (SQL/timing/rows/comparisons)
framework/database/audit/          AuditLogger — structured logging of DB activity
```

Full detail: [DatabaseFramework.md](DatabaseFramework.md),
[RepositoryPattern.md](RepositoryPattern.md),
[DatabaseConfiguration.md](DatabaseConfiguration.md),
[DatabaseBestPractices.md](DatabaseBestPractices.md).

## framework/testdata/ — the Test Data Management platform

A fourth sibling — no automated test should contain hardcoded business
data; every value comes from this layer instead:

```
framework/testdata/generators/    RandomData extension, TelecomIdentifierGenerator (Luhn-valid
                                   IMEI/ICCID, IMSI/MSISDN), DeterministicGenerator, CustomGeneratorRegistry
framework/testdata/builders/      BaseBuilder + 8 domain builders — produce framework.database.models
                                   dataclasses directly, not parallel DTOs
framework/testdata/factories/     Canned Factory-Method instances built on the builders
framework/testdata/scenarios/     ScenarioLibrary — 10 named, reusable, referentially-consistent scenarios
framework/testdata/datasets/      DatasetLoader (JSON/YAML/CSV/Excel; versioned/shared/scenario files)
framework/testdata/providers/     DataProvider — one fetch(key) interface over DB/API/JSON/CSV/Excel/env
framework/testdata/validators/    Schema, format (incl. Luhn), business-rule, uniqueness, relationship
framework/testdata/masking/       DataMasker, PII field registry, Fernet encryption (reused, not duplicated)
framework/testdata/synthetic/     SyntheticDatasetGenerator (bulk), Anonymizer
framework/testdata/seed/          DatabaseSeeder, ApiSeeder, SeedOrchestrator
framework/testdata/cleanup/       CleanupRegistry, DatabaseCleanupService, ApiCleanupService,
                                   UiCleanupHooks, RollbackManager
framework/testdata/fixtures/      pytest fixtures: seeded_scenario, load_dataset, build_scenario, cleanup_registry
```

Deliberately built on existing layers rather than beside them: builders
produce `framework.database.models` dataclasses directly (a `Tenant` built
here is the same `Tenant` `TenantRepository.create()` accepts), `Database
Seeder`/`DatabaseCleanupService` are thin wrappers over the repository
layer's `UnitOfWork`, and `ApiSeeder`/`ApiCleanupService` reuse `ApiClient`.
`framework/hybrid`'s `ValidationFacade` is untouched by this layer's
existence — a hybrid test built on TDM-sourced data uses the exact same
`facade.verify_api`/`verify_database` calls as one using hand-written data.

Full detail: [TestDataFramework.md](TestDataFramework.md),
[BuilderPattern.md](BuilderPattern.md), [ScenarioLibrary.md](ScenarioLibrary.md),
[DatasetManagement.md](DatasetManagement.md), [SyntheticData.md](SyntheticData.md),
[CleanupStrategy.md](CleanupStrategy.md), [BestPractices.md](BestPractices.md).

## UI Automation Architecture (Milestone 3)

### Call chain

A test never touches Playwright. Each layer only calls the one below it:

```
tests/                     "search for subscriber X, expect to find them"
  ↓
framework/workflows/       SubscriberSearchWorkflow — opens the module, searches, returns a result
  ↓
framework/navigation/      AppNavigator — "go to Subscriber Management" (sidebar/tab click)
  ↓
framework/pages/<module>/  SubscriberManagementPage — business actions: search_subscriber(name)
  ↓
framework/components/      TableComponent — headers()/rows()/find_row_index()/click_row_action()
  ↓
framework/pages/base_page.py + framework/waits/  BasePage delegates non-trivial waits to WaitManager
  ↓
Playwright (Page/Locator)
```

Assertions (`framework/assertions/UIAssert`, plus per-module assertion
helpers like `SubscriberAssertions`) sit beside this chain, not inside it —
a test calls a Page/Workflow to *do* something, then calls an assertion
helper to *check* something, matching the Assert/SoftAssert convention the
UI layer already used pre-Milestone-3.

### Component relationships

```
BasePage ─────────────┐
  (per-screen)         │  both delegate non-trivial waits to WaitManager,
                        │  build locators via Locators (testid > role > label > css > xpath)
BaseComponent ─────────┘
  (per-widget, root-scoped)
        │
        ├── HeaderComponent, SidebarComponent, TopNavigationComponent, BreadcrumbComponent
        │       ↑ composed by AppNavigator ("go to module X")
        ├── TableComponent, PaginationComponent, GridComponent   (data display)
        ├── ModalComponent, ConfirmationDialogComponent, NotificationComponent  (overlays)
        └── SearchBoxComponent, DatePickerComponent, DropdownComponent, TreeViewComponent  (input widgets)
```

A `BaseComponent` is scoped to a root `Locator`, so a `TableComponent` used
inside a `ModalComponent` and one used directly on the page never collide —
each instance only ever looks inside its own root element. Page Objects
compose components as attributes (`SubscriberManagementPage.table =
TableComponent(page, "#table1")`) rather than reimplementing table logic
per screen.

### Workflow Layer

A Workflow composes one or more Page Objects (and, when a test needs it,
`AppNavigator`) into a single business-level call:

```python
class SubscriberSearchWorkflow:
    def execute(self, last_name: str) -> dict[str, str] | None:
        subscriber_page = SubscriberManagementPage(self.page)
        subscriber_page.base_url = self.base_url
        subscriber_page.open()
        return subscriber_page.search_subscriber(last_name)
```

Workflows exist for flows that genuinely span more than one Page Object or
that enough tests repeat verbatim to be worth naming once
(`LoginWorkflow`, `LogoutWorkflow`, `SubscriberSearchWorkflow`,
`PolicyCreationWorkflow`, `UserCreationWorkflow`). A single-page action
doesn't need a workflow wrapper — call the Page Object directly.

### Page Layer

Every Page Object:
- extends `BasePage`, sets `path` (appended to `base_url`)
- exposes **business actions only** — `search_subscriber(name)`, never
  `click("#search-button")` from a test
- keeps locators as class constants (or `Locators.*` calls), never inline
  strings scattered through methods
- returns either a plain value (`dict`, `str`, `bool`) or the next Page
  Object reached (`LoginPage.login() -> DashboardPage`), so a test's call
  chain reads as a sequence of business steps

Each sample module under `framework/pages/<module>/` follows the same
four-file shape: `page.py` (the Page Object), `assertions.py`
(module-specific checks built on `UIAssert`/`Assert`), `test_data.py`
(a Pydantic-model dynamic builder), `__init__.py` (re-exports). Static
fixed data lives in `data/testdata/<module>/` instead, loaded via
`TestDataLoader`.

**Module status**: Authentication (`LoginPage`) and Dashboard
(`DashboardPage`) are real, from Milestone 1. Subscriber Management is real
and live-verified against the-internet.herokuapp.com's `/tables` demo as a
stand-in data grid (same convention as Authentication/Dashboard) — a
deliberate choice, since this is a generic, customer-agnostic framework
with no single "real" target application of its own. Policy
Management, Alarm Management, Reports, Administration, Audit Logs, and User
Management are genuine, complete code (Page Object + Workflow + Assertions
+ Test Data + example test) but their example tests are `pytest.mark.skip`'d
with an explicit reason — there's no real environment to run them against
yet. Swapping in real selectors once the actual app is available shouldn't
require changing any test that calls these Page Objects, since tests only
ever call named business actions.

### Best practices this framework enforces structurally

- **No raw locators in test files** — enforced by convention (Page Objects
  own selectors), not by tooling; code review is the gate.
- **No hardcoded waits** — `BasePage`/`BaseComponent` route every
  non-trivial wait through `WaitManager`; `page.wait_for_timeout(N)` should
  never appear outside `WaitManager`'s own bounded-poll implementation.
- **Locator priority is explicit** — `Locators` documents and enforces
  data-testid > role > aria-label > css > xpath, with xpath usage logged as
  a warning so it surfaces in review.
- **Failure artifacts are automatic, not opt-in** — `DriverManager`
  (Milestone 1) captures screenshot/trace/video on failure for every test
  without the test author doing anything.
- **One browser context per test** — the `page` fixture is function-scoped,
  so `pytest-xdist -n auto` parallelizes safely; nothing in the UI layer
  holds cross-test state (see the visual-testing baseline-naming fix in
  `tests/visual/` for a concrete example of this being enforced, not just
  claimed).

## Patterns in use today

| Pattern | Where | Why |
|---|---|---|
| Factory | `BrowserFactory.launch()`, `AuthFactory.from_config()` | One call site decides Chromium/Firefox/WebKit + channel (Chrome/Edge), or which `httpx.Auth` strategy, from config — hiding the underlying library's construction differences from every caller. |
| Facade | `BasePage` (UI), `ApiClient` (API) | Wraps raw Playwright/httpx calls with logging + framework exceptions, so page/service classes read as business actions, not library calls. |
| Repository | `framework/database/repositories` | Exposes `find_by_msisdn(x)` style methods, not raw SQL — swapping Oracle/Postgres/MySQL/SQL Server/SQLite is a config change, never touches a repository or a test. |
| Unit of Work | `framework/database/services/unit_of_work.py` | Coordinates several repositories under one transaction so their writes commit — or roll back — together, without a test manually juggling connections. |
| Strategy | `httpx.Auth` subclasses (`framework/api/auth`); `ValidationMode` → `ValidationFacade` (`framework/hybrid`) | Auth: which credential-handling logic runs is chosen by which strategy object is passed in, not a branch in `ApiClient`. Validation mode: which of a hybrid test's `verify_api`/`verify_database` calls actually execute is chosen by config (`ui_only` / `ui_api` / `ui_database` / `ui_api_database`), not by which test class you inherit from. |
| Builder | `EnvironmentSettings` loader (`framework/config/settings.py`); `RequestBuilder` (`framework/api/builders`) | Settings: merges YAML + `.env` + process env into one validated, immutable object. Requests: assembles headers/params/body into a `RequestSpec` through a fluent chain. |
| Singleton (scoped) | `get_settings()` | `lru_cache`'d per environment — one validated settings object per test session, not re-parsed per test. |
| Page Object / Page Component | `framework/pages`, `framework/components` | Screens vs. reusable widgets (nav bars, modals, tables) are modeled separately so a widget used on 10 pages is written once. |
| Composite | `AppNavigator` (`framework/navigation`) | Composes `SidebarComponent`/`TopNavigationComponent`/`BreadcrumbComponent` behind one `go_to_module()` call — a Workflow doesn't know or care which nav widget actually gets it there. |
| Facade (again) | `WaitManager` (`framework/waits`) | Every non-trivial wait condition (network idle, API response, loader-gone, toast, DOM-stable) is one class, so "no hardcoded waits" is enforceable by code review — there's exactly one place a real wait condition can live. |

## Hybrid validation (UI / API / DB) — implemented (Milestone 4)

The intent (see `framework/enums/validation_mode.py`) is that a test calls
the same validation code regardless of what's actually being checked
underneath:

```python
facade.verify_api(lambda: api_validator.verify_dashboard(user))
facade.verify_database(lambda: database_validator.verify_dashboard(user))
```

Under `ui_only`, neither callable executes (UI assertions elsewhere in the
test still run — they're not gated). Under `ui_api_database`, both execute,
hitting a real API and a real database. Which one runs is decided entirely
by `validation_mode` in `config/environments/<env>.yaml` — switching
environments never means editing test code.

`ApiValidator` (`framework/api/services/api_validator.py`) answers "is this
true according to the backend" for the API leg; the 6 domain validators in
`framework/database/validators` (built on `DataComparator`) do the same for
the database leg, each comparing one expected record against the database,
an API payload, and/or a UI-read value. `ValidationFacade`
(`framework/hybrid/validation_facade.py`) is the dispatcher, and
`framework.hybrid.fixtures`/`framework.database.fixtures.database_fixtures`
supply the pytest fixtures (`validation_facade`, `subscriber_repository`,
etc.) a hybrid test declares alongside `page`/`api_client`. Full detail,
including the exact fixture list and a worked example against real
backends: [HybridValidation.md](HybridValidation.md).

## Execution model

- One `DriverManager` instance per test → one browser context per test →
  `pytest-xdist -n auto` parallelizes safely because tests never share browser
  state.
- Artifacts (screenshot/trace/HAR/video) are only persisted on failure, so
  green runs stay cheap and CI storage doesn't balloon.
- `pytest_runtest_makereport` stashes the test outcome on the pytest item so
  the `page` fixture's teardown (which runs after the test body) knows whether
  to keep or discard artifacts.

## Configuration

`config/environments/{dev,qa,uat,preprod,production}.yaml` hold structure
(URLs, timeouts, feature flags); actual secrets are never committed — YAML
values reference `${ENV_VAR:-default}` placeholders resolved from `.env` /
process environment at load time (`framework/config/settings.py`).
