# Cleanup Strategy

How `framework/testdata/cleanup/` and `framework/testdata/seed/` guarantee
test data created for a test doesn't outlive it — across the database, an
API, and (optionally) the UI.

## The problem this solves

A test that seeds a tenant/subscriber/steering zone but never deletes them
leaves the target database/API growing forever, and eventually collides
with itself (unique-constraint violations on a second run) or pollutes
another test's query results. "Automatic cleanup after tests" means this
can't be forgotten — it happens via fixture teardown, not a line at the end
of every test body that's easy to skip or that never runs if the test
fails before reaching it.

## `CleanupRegistry` — the core mechanism

```python
registry = CleanupRegistry()
registry.register(lambda: some_service.delete(thing))
...
errors = registry.execute_all()   # LIFO order, collects (doesn't raise) exceptions
```

- **LIFO order**: mirrors creation-dependency order. If B was created after
  A because it depended on A (a subscriber created after its tenant), B
  must be deleted before A.
- **Collects, doesn't abort on, exceptions**: one failing cleanup callback
  must not prevent the rest from running — `execute_all()` runs every
  registered callback regardless, and returns whatever exceptions occurred
  so the caller can decide whether to surface them.
- **pytest integration**: the `cleanup_registry` fixture
  (`framework/testdata/fixtures/testdata_fixtures.py`) yields a fresh
  registry per test and calls `execute_all()` at teardown — which pytest
  runs whether the test passed, failed, or errored.

## Layer-specific cleanup services

| Service | Deletes via | Notes |
|---|---|---|
| `DatabaseCleanupService` | the repository layer, inside one `UnitOfWork` | Alarms are intentionally excluded (`AlarmRepository` has no `delete()`, only `clear_alarm()` — matching real alarm-lifecycle semantics) |
| `ApiCleanupService` | `ApiClient.delete()` against a `{id}`-templated endpoint | reuses `ApiClient`'s retry/logging/Allure middleware |
| `UiCleanupHooks` | page-driven actions (`clear_storage`, `clear_cookies`, `logout_via`) | deliberately thin — most real UI cleanup is app-specific and belongs in the page object itself |

## The `seeded_scenario` fixture: seed + cleanup in one call

```python
def test_x(seeded_scenario, subscriber_repository):
    handle = seeded_scenario("roaming_subscriber")
    # ... use handle.database_entities ...
    # nothing else needed — cleanup is already registered
```

Internally: `seeded_scenario` calls `DatabaseSeeder.seed_scenario()`, then
registers `DatabaseCleanupService.delete(seeded_entities)` with the test's
`cleanup_registry`. A test never has to remember cleanup exists.

## Two strategies for database state: delete vs. rollback

| | `DatabaseCleanupService` (delete after commit) | `RollbackManager` (never commit) |
|---|---|---|
| Test can see its own writes from a second connection (e.g. a real API call that queries the DB independently) | Yes | No |
| Survives a hard crash mid-test without leaking data | No (delete step might not run) | Yes (nothing was ever committed) |
| Cost | One DELETE per entity at teardown | None — rollback is free |

Prefer `RollbackManager.rollback_scope()` for tests that never need a
second connection to observe their writes; prefer `DatabaseCleanupService`
(via `seeded_scenario`) otherwise — this milestone's hybrid tests use the
latter because the API leg (a separate real HTTP call) needs to see
committed state.

## Verified, not just described

`tests/testdata/integration/test_seed_and_cleanup.py` and
`test_fixtures.py` — 15 tests against a real database: seed-then-verify,
cleanup-then-verify-gone, LIFO ordering, error resilience (one failing
callback doesn't block the rest), and the `seeded_scenario` fixture
actually registering exactly one cleanup callback per call.
