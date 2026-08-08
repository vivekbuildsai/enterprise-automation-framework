# Database Best Practices

Practices this framework enforces or assumes — several of these are lessons
from real failures caught while verifying `tests/database` against actual
PostgreSQL/MySQL containers (not just SQLite) during this milestone, kept
here so they don't get relearned the hard way.

## Never write SQL in a test

All SQL lives in `framework/database/queries/*.py`. A test calls
`subscriber_repository.find_by_msisdn(x)`, never
`connection.execute("SELECT ...")`. See
[RepositoryPattern.md](RepositoryPattern.md) for why.

## Write dialect-portable DDL — always verify against more than SQLite

SQLite is dramatically more lenient than PostgreSQL/MySQL/Oracle/SQL Server
about types and identity columns. Two real examples caught by this
milestone's own verification pass (running the same suite against real
Postgres/MySQL, not just SQLite):

1. **Never rely on autoincrement/`SERIAL`/`IDENTITY`.** SQLite's
   `INTEGER PRIMARY KEY` silently auto-assigns a rowid when the column is
   omitted from an `INSERT`. PostgreSQL does not — the same `INSERT` fails
   with a `NotNullViolation`. This framework's entire demo schema
   (`framework/database/queries/*.py`) instead uses app-generated `VARCHAR`
   primary keys everywhere, specifically so the same DDL and the same
   `INSERT` statements work unmodified across all five dialects.
2. **Make ad-hoc DDL in tests idempotent.** SQLite (`:memory:`) starts fresh
   every process; a real PostgreSQL/MySQL container is *persistent* across
   test runs. A test that does `CREATE TABLE t (...)` without
   `DROP TABLE IF EXISTS t` first passes once against SQLite and then fails
   with "relation already exists" the second time it runs against a real,
   already-populated server. `SchemaManager`'s `CREATE TABLE IF NOT EXISTS`
   already follows this rule for the framework's own schema; any additional
   ad-hoc table a test creates must too (see `tests/database/regression/
   test_query_executor.py`/`test_transaction_manager.py` for the pattern).

**The practical takeaway: SQLite-only verification is not sufficient
evidence that dialect-portable code actually is portable.** This framework's
CI (`test-database` job) runs the identical suite against SQLite,
PostgreSQL, and MySQL specifically to catch this class of bug automatically,
rather than trusting that "it passed" once against the easy dialect.

## Use `UnitOfWork` when more than one repository must commit together

A single repository call already runs inside a transaction. Reach for
`UnitOfWork` specifically when two or more repositories' writes must
succeed or fail as one unit (e.g. updating a subscriber's status *and*
recording an audit entry) — see [RepositoryPattern.md](RepositoryPattern.md).
Don't manually coordinate two separate connections/transactions for this;
that's exactly the bug class `UnitOfWork` exists to prevent.

## Pick the right transaction mode deliberately

- `TransactionMode.COMMIT` (default) — normal writes that should persist.
- `TransactionMode.ROLLBACK` — a test that must leave zero trace, even on
  success (e.g. probing an insert's side effects without keeping the row).
- `TransactionMode.READ_ONLY` — same mechanics as `ROLLBACK`, but names the
  *intent* ("this was never meant to write") rather than "discarding
  writes" — prefer it for genuinely read-only test bodies so a future
  reader doesn't have to guess why writes are being thrown away.

## Never assert exact values on time-variant data

Usage counts, "yesterday's" metrics, and similar continuously-changing
values — anything the real application (or a live external dependency)
generates continuously — should be asserted on shape (row count, column
presence, value type/range), not exact values. This applies equally to
database rows sourced from a live system once this framework is pointed
at one.

## Seed/cleanup discipline

- `SchemaManager.create_all()` is idempotent (`CREATE TABLE IF NOT EXISTS`)
  — safe to call every test via the `db_schema` fixture without checking
  "does the table already exist" yourself.
- `CleanupManager.truncate_all()` (called automatically by `db_schema`'s
  teardown) empties every table but doesn't drop them — cheap, and
  guarantees the next test starts from zero rows even though the schema
  itself, and the underlying connection pool, persist across tests within
  one session.
- `SeedManager.seed_baseline()` uses `framework.utilities.RandomData` (the
  same Faker wrapper the UI test-data layer uses) for values that don't need
  to be fixed, and fixes exactly the fields a test is likely to assert on
  (e.g. one zone with `leakage_flag=1`, one with `anti_sor_flag=1`) so tests
  built on it stay deterministic where it matters.

## Hybrid tests hit real external systems — expect their limits

`tests/database/integration/` deliberately exercises real backends (the
same the-internet.herokuapp.com / dummyjson.com sandboxes the UI/API suites
already use) rather than mocks, because the point is proving cross-layer
validation actually works end-to-end. That means an occasional transient
failure — a `429` from dummyjson.com's request-rate cap when the full test
session hits it repeatedly in a short window — is the sandbox's limit, not
a framework defect. Re-running the single failing test after a short wait
is the correct response, not weakening the assertion.

## Credentials

Never log a resolved password. `CredentialResolver` supports both
`${AUTOMATION_DB_PASSWORD}` env-var substitution (plaintext only ever in the
environment/`.env`, never in a tracked file) and `encrypted_password`
(Fernet ciphertext safe to commit, decrypted via `AUTOMATION_DB_SECRET_KEY`) — see
[DatabaseConfiguration.md](DatabaseConfiguration.md#encrypted-credentials).
Pick whichever your environment's secrets policy requires; both resolve to
the same `DatabaseConfig`/`ConnectionFactory` code path.
