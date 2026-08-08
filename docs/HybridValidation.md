# Hybrid Validation

How `framework/hybrid/ValidationFacade` lets one test body validate UI-only,
UI+API, UI+DB, or UI+API+DB — selected purely by
`validation_mode` in `config/environments/<env>.yaml` (or
`AUTOMATION_VALIDATION_MODE`) — with **zero test-code changes** between modes.
This closes the gap `docs/APIFramework.md`'s "Hybrid validation" section
left open (`ApiValidator` existed; nothing wired it, or a DB equivalent,
into a shared UI test yet).

## The four modes

```python
class ValidationMode(StrEnum):
    UI_ONLY = "ui_only"
    UI_API = "ui_api"
    UI_DATABASE = "ui_database"
    UI_API_DATABASE = "ui_api_database"
```

`ValidationFacade(mode)` exposes `ui_enabled` (always `True`), `api_enabled`,
and `database_enabled` computed from `mode` — and three methods that either
run or skip the callable they're handed:

```python
facade.verify_ui(check)         # always runs
facade.verify_api(check)        # runs iff mode includes API
facade.verify_database(check)   # runs iff mode includes database

facade.run(ui=..., api=..., database=...)   # all three in one call
```

A **callable**, not the result of calling it, is passed in specifically so
a disabled layer costs nothing — an API call or DB query behind a skipped
lambda never executes.

## The shape from the brief

```python
def test_login_verified_across_layers(page, settings, api_validator,
                                       subscriber_repository, validation_facade):
    login_page = LoginPage(page)
    dashboard = login_page.login(user)
    dashboard.verify_dashboard()                                          # UI, always

    validation_facade.verify_api(lambda: api_validator.verify_dashboard(user))
    validation_facade.verify_database(lambda: database_validator.verify_dashboard(user))
```

Switch `validation_mode: ui_only` -> `ui_api_database` in YAML and the exact
same test starts exercising the API and DB checks — see
`tests/database/integration/test_hybrid_business_flow.py` for the real,
passing version of this (against the-internet.herokuapp.com for UI,
dummyjson.com for API, and the SQLite/Postgres/MySQL demo schema for DB).

`tests/database/integration/test_hybrid_validation_facade.py` proves the
dispatch itself: one test, parametrized over all four `ValidationMode`
values, asserting the exact set of layers that actually ran matches what
each mode should select — against three real backends, not mocks.

## Fixtures

| Fixture | From | Purpose |
|---|---|---|
| `validation_facade` | `framework.hybrid.fixtures` | `ValidationFacade(settings.validation_mode)` |
| `database_manager`, `db_connection`, `db_executor` | `framework.database.fixtures.database_fixtures` | Session engine, function-scoped connection/executor |
| `subscriber_repository`, `tenant_repository`, ... | same | One fixture per domain repository |
| `unit_of_work_factory` | same | `uow_factory(mode=...)` -> `UnitOfWork` |
| `db_schema` | same | Creates the demo schema, truncates on teardown |
| `seeded_baseline` | same | `db_schema` + a ready-made tenant/network/subscribers/zones |

All four registered as pytest plugins in `tests/conftest.py` alongside the
existing `driver_fixtures`/`api_fixtures` — a hybrid test just declares
whichever fixtures it needs (`page`, `api_client`/`api_validator`,
`subscriber_repository`, `validation_facade`, ...); nothing about how they
combine is hardcoded into a single "god fixture".

## Cross-layer comparison

Under the hood, both `ValidationFacade`-gated checks and the 6 domain
validators (`framework.database.validators`) use `DataComparator`
(`framework.database.utilities.comparison`) for the actual field-by-field
comparison:

```python
DataComparator.compare_ui_api(ui_values, api_payload)
DataComparator.compare_api_db(api_payload, db_row)
DataComparator.compare_ui_db(ui_values, db_row)
DataComparator.compare_all(ui_values, api_payload, db_row)   # all three pairwise
```

Every comparison is case/whitespace-insensitive for strings (a UI showing
`"Active"` and a DB column storing `"ACTIVE"` is a match, not a false
failure) and produces a human-readable diff via `ComparisonResult.to_report()`
— attached to Allure automatically, and available directly to assert on or
raise (`.raise_if_mismatched()`) in test code.

## What this does *not* do

- It does not invent a new assertion DSL — `verify_api`/`verify_database`
  wrap ordinary callables; write whatever assertions make sense inside them
  (`ApiValidator` calls, `DataComparator` calls, plain `assert`).
- It does not require every test to use all three layers — a UI-only test
  simply never calls `verify_api`/`verify_database`, and costs nothing extra.
- It does not retry a rate-limited public sandbox API for you — dummyjson.com
  (used by the existing API suite and these hybrid tests) enforces a request
  cap; an occasional `429` from a hybrid test run back-to-back with the full
  API suite is the sandbox's rate limit, not a framework defect (see
  [DatabaseBestPractices.md](DatabaseBestPractices.md)).
