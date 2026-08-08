# Examples

**Start here if you only read one thing: [`data_validation/`](data_validation/)
is this framework's key differentiator — end-to-end UI + API + Database
validation.** Everything below is a small, **executable** example — real
framework APIs, no fake code that "looks impressive but can't run." All of
them pass right now:

```bash
poetry install --no-root
poetry run python -m playwright install chromium
poetry run pytest examples/ -v
```

They live outside `tests/` on purpose (`pyproject.toml`'s `testpaths =
["tests"]` never auto-collects them) — this is demo code, clearly
separated from the framework's own CI-gated test suite and from
`framework/` itself. None of them use customer-specific terminology, real
credentials, or a real customer URL — they run against the framework's
public sample UI target (the-internet.herokuapp.com), a public fake-data
API (dummyjson.com), fully local mocks, or small sanitized fixture data
written for the example.

| # | Example | Capability | Requires |
|---|---|---|---|
| A | [`ui_automation/`](ui_automation/) | Core — UI automation | A browser (Playwright) |
| B | [`data_validation/`](data_validation/) `test_widget_vs_database_example.py` | Core — UI → network → DB → tolerance | A browser only (DB is a local fake) |
| **F** | [`data_validation/`](data_validation/) `test_ui_api_database_validation_example.py` | **Core — the framework's key differentiator: end-to-end UI → real API → Database validation** | A browser + internet access to dummyjson.com (DB is local SQLite) |
| C | [`framework_sync/`](framework_sync/) | Framework Sync (optional) | Nothing — pure local analysis |
| D | [`discovery/`](discovery/) | Application Discovery (optional) | A browser (for the UI half) |
| E | [`ai_assistance/`](ai_assistance/) | AI Assistance (optional) | Nothing — AI is never required |

## A — UI Automation

`ui_automation/test_login_and_table_example.py` — Playwright, a Page
Object (`LoginPage`/`DashboardPage`), a Component (`TableComponent`, via
`SubscriberManagementPage`), the `Assert` facade, and Allure reporting.
Runs against the public demo target.

## B — UI + Backend/Data Validation (the key differentiator)

`data_validation/test_widget_vs_database_example.py` — the full pipeline
this framework is built around:

```
UI action -> NetworkInterceptor -> WidgetDataExtractor -> normalization
    -> DashboardRepository (database source of truth) -> DataComparator
    + Tolerance -> ComparisonResult
```

Entirely local: a mocked network response stands in for a live dashboard,
and a fake ClickHouse client (same pattern the framework's own test suite
uses — no real ClickHouse server available) stands in for the database.
Uses the real `config/dashboards/sample_dashboard.json`.

## F — UI + API + Database Validation (end-to-end, the key differentiator)

`data_validation/test_ui_api_database_validation_example.py` — the same
idea as B, but through `framework.hybrid.ValidationFacade` with a **real**
API call instead of network interception, showing the other supported
path through this framework's core differentiator:

```
UI (LOCAL page) -> ValidationFacade.verify_ui
API (REAL: GET https://dummyjson.com/users/1) -> ValidationFacade.verify_api
Database (LOCAL: SQLite, seeded by the example) -> ValidationFacade.verify_database
    -> DataComparator + Tolerance -> ComparisonResult
```

One config value (`validation_mode`) decides which of `verify_api`/
`verify_database` actually run — the test body never changes. No
customer-specific or internal domain models: every value is a plain
`dict`, exactly like example B. REAL/LOCAL is labeled explicitly per
layer in the file's own docstring — the API call is genuinely real (no
account or key needed), the UI and database are local stand-ins since no
public demo site exposes this exact API's data through a real web UI.

## C — Framework Sync

`framework_sync/test_analyze_sample_repo_example.py` analyzes
`framework_sync/sample_legacy_repo/` (a tiny, sanitized Selenium+pytest
fixture written for this example) end to end: `RepositoryAnalyzer.analyze()`
→ `compute_compatibility_report()` → `generate_migration_worksheet()`.
Mode 1 and Mode 2 only — Modes 3/4 remain unimplemented, as documented in
[docs/FrameworkSync.md](../docs/FrameworkSync.md).

## D — Application Discovery

`discovery/test_ui_and_api_discovery_example.py` — `UIDiscoveryEngine`
against a local sample page (showing the real test-id > role > label
priority ladder) and `discover_from_openapi()` against a small sample
spec, saved as one `DiscoveryReport`.

## E — Optional AI

`ai_assistance/test_optional_ai_recommendation_example.py` — two tests:
one with the default `DisabledProvider` (no configuration, no network
call — proves Discovery works completely without AI), one with a mocked
`OpenAICompatibleProvider` showing what a real suggestion + confidence
level looks like. Neither talks to a real AI service.

## Design principle

Every example calls real, already-tested framework code — nothing here is
reimplemented just for the demo. Where a live external dependency isn't
available in a generic/CI environment (a real ClickHouse server, a real
AI provider), the example says so explicitly and uses the same
mocking/faking pattern the framework's own test suite already uses,
rather than skipping the step or faking success.
