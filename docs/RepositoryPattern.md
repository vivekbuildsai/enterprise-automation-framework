# Repository Pattern

Why `framework/database/` is layered `queries -> repositories -> services`
instead of tests (or repositories) writing SQL directly.

## The three layers

```
queries/subscriber_queries.py     Raw SQL, as named SQLAlchemy TextClause constants
repositories/subscriber_repository.py    Row<->model mapping + domain-specific finders
services/unit_of_work.py                 Coordinates several repositories under one transaction
```

**No SQL lives outside `queries/*.py`.** A repository method looks like:

```python
class SubscriberRepository(BaseRepository[Subscriber]):
    model = Subscriber

    def find_by_msisdn(self, msisdn: str) -> Subscriber | None:
        row = self._executor.fetch_one(SubscriberQueries.FIND_BY_MSISDN, {"msisdn": msisdn})
        return self._map_one(row)
```

`SubscriberQueries.FIND_BY_MSISDN` is `text("SELECT * FROM subscribers WHERE msisdn = :msisdn")`
— a plain SQLAlchemy `TextClause`, parametrized, dialect-portable. Nothing
about it is Subscriber-specific logic; it's just the query. The
Subscriber-specific part — "what does 'find by msisdn' *mean*, and what do
I do with zero vs. one row" — lives in the repository.

## Why this split, specifically

- **A test never writes SQL.** `subscriber_repository.find_by_msisdn(x)` is
  the vocabulary a test uses; the SQL behind it can change (add a WHERE
  clause, switch to a view) without touching a single test.
- **A query is reusable across repository methods** without duplicating SQL
  text — `SteeringQueries.FIND_BY_TENANT` is used by both
  `find_by_tenant()` and (indirectly) `find_with_leakage()`'s sibling query.
- **Dialect portability is enforced in one place.** Every `queries/*.py`
  module follows the same rule (VARCHAR primary keys, ISO-8601 string
  timestamps, no dialect-specific syntax) — see
  [DatabaseBestPractices.md](DatabaseBestPractices.md). A repository method
  can't accidentally introduce a Postgres-only construct because it never
  writes SQL to begin with.
- **Testing gets cheaper.** `ResultMapper`/`QueryExecutor` are unit-tested
  against plain dicts and a real (SQLite) connection independent of any
  specific domain; each repository's tests only need to verify its own
  finder methods, not re-prove the mapping/execution machinery.

## `BaseRepository[T]`

```python
class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, executor: QueryExecutor) -> None: ...
    def _map_one(self, row: dict | None) -> T | None: ...
    def _map_many(self, rows: list[dict]) -> list[T]: ...
    def require_one(self, row, *, not_found_message: str) -> T: ...   # raises RepositoryError
```

Every domain repository (`SubscriberRepository`, `TenantRepository`,
`NetworkRepository`, `SteeringRepository`, `AuditRepository`,
`AlarmRepository`, `SystemRepository`) sets `model` to its dataclass
(`framework.database.models`) and builds its own `get_by_id`/`find_*`
methods on top of `_map_one`/`_map_many`/`require_one` — deliberately
**not** a generic `get_by_id(id_column, id_value)` on `BaseRepository`
itself, because different domains key on different columns
(`subscriber_id` vs. `zone_id` vs. `config_key`) and a generic version would
either need reflection or lose type safety for no real benefit at this
scale.

## Unit of Work

A single repository call already runs inside a connection/transaction (via
`db_executor`/`db_connection` fixtures, or a `UnitOfWork`'s own connection).
`UnitOfWork` exists for the case where **more than one repository** needs to
commit — or roll back — together:

```python
with UnitOfWork(database_manager, "subscriber_db") as uow:
    subscribers = uow.repository(SubscriberRepository)
    audit = uow.repository(AuditRepository)

    subscribers.update_status(subscriber_id, "SUSPENDED", updated_at=now)
    audit.record(AuditLogEntry(action="STATUS_CHANGE", ...))
# both commit together; if either raises, both roll back
```

Repositories requested from the same `UnitOfWork` are cached and share its
one connection/transaction — asking for `SubscriberRepository` twice returns
the same instance, not two repositories racing on separate connections.

## Testing strategy

- `tests/database/regression/test_repositories.py` — one test per domain,
  full CRUD-ish round trip against a real (SQLite/Postgres/MySQL) connection
  via the `db_schema` fixture — no mocking; a repository test that passes
  proves the SQL is actually correct for whichever dialect the suite is
  pointed at.
- `tests/database/regression/test_unit_of_work.py` — commit-together and
  roll-back-together behavior, plus that repository instances are cached
  within one `UnitOfWork`.
- `tests/database/regression/test_query_executor.py` /
  `test_result_mapper.py` — the layer underneath repositories, tested once,
  independent of any domain.
