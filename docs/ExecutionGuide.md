# Execution Guide

Covers the API suite (Milestone 2), the Database/Hybrid suite (Milestone 4
— see [DatabaseFramework.md](DatabaseFramework.md) and
[HybridValidation.md](HybridValidation.md)), and the Test Data Management
suite (Milestone 5 — see [TestDataFramework.md](TestDataFramework.md)). UI
suite execution is covered in [GettingStarted.md](GettingStarted.md).

## API Suite

### Local

```bash
poetry install --no-root
cp .env.example .env

# All API tests (smoke + regression, live against dummyjson.com)
poetry run pytest tests/api -v

# Just smoke
poetry run pytest tests/api/smoke -v -m smoke

# Just the negative-path/regression suite
poetry run pytest tests/api/regression -v -m regression

# Parallel
poetry run pytest tests/api -n auto

# With Allure results + coverage
poetry run coverage run --source=framework/api -m pytest tests/api
poetry run coverage report -m
```

### What's live vs. offline

- `tests/api/smoke/`, `tests/api/regression/test_user_crud_regression.py`,
  `tests/api/regression/test_negative_cases.py` — hit the real
  `dummyjson.com` over the network.
- `tests/api/regression/test_*_unit.py` — offline, built on
  `httpx.MockTransport`. No network required; these are what keep CI fast
  and non-flaky, and cover the framework's own retry/auth/validation logic
  (including edge cases the live suite can't reliably trigger, like a
  persistent 503).

Both run under the same `pytest tests/api` invocation — the split is by
filename convention (`*_unit.py`), not a separate marker, so no special
flag is needed to run "just the fast ones" vs. "just the real ones" today.
If the live suite ever needs to be excluded (e.g. no network in a sandboxed
CI runner), the `smoke`/`regression` markers combined with a `-k` filter on
filename work: `pytest tests/api -k "unit"`.

### Running against a different environment

```bash
AUTOMATION_ENV=qa poetry run pytest tests/api/regression -v
```

Reads `config/environments/qa.yaml` — add an `api:` entry there for whatever
service you're targeting (see [Authentication.md](Authentication.md) for the
config shape). `dev.yaml` is the only environment wired to the public
`dummyjson` sample today.

### Docker

```bash
docker compose build
docker compose run --rm automation pytest tests/api -v
```

The image already has everything the API suite needs (`httpx`, `pydantic`,
`jsonschema` etc. are plain Python deps — no browser binaries required for
API-only runs, though the image includes them for the UI suite too).

### CI

`.github/workflows/ci.yml`'s `test-api` job runs the API suite with
coverage. See that file for the exact steps.

### Debugging a failing API test

1. Structured logs (`logs/execution.log` or console) show every request/response
   with a correlation ID, redacted secrets, status, and timing — find the
   failing correlation ID and read both lines.
2. Allure attaches the full request/response (headers + body) to the test
   result — `allure serve reports/allure-results` if you have the Allure CLI.
3. For a schema failure, the exception message names every failing field —
   no need to diff the schema by hand.
4. For a flaky live test, re-run just that one against `dummyjson.com`
   directly with `curl` first to rule out the provider being down/changed
   before assuming a framework bug.

## Database & Hybrid Suite

### Local (SQLite — zero setup)

```bash
poetry install --no-root
cp .env.example .env

# All database tests (smoke + regression) — SQLite in-memory, no server needed
poetry run pytest tests/database -m "database and not integration" -v

# Just smoke (connectivity)
poetry run pytest tests/database/smoke -v -m smoke

# Hybrid (UI+API+DB) integration tests — needs Playwright browsers installed
poetry run python -m playwright install chromium
poetry run pytest tests/database/integration -v -m hybrid
```

### Against a real PostgreSQL / MySQL server

```bash
docker compose up -d postgres          # or: mysql

AUTOMATION_DB_DIALECT=postgresql AUTOMATION_DB_HOST=localhost AUTOMATION_DB_PORT=5432 \
AUTOMATION_DB_NAME=sample_app AUTOMATION_DB_USER=automation_qa AUTOMATION_DB_PASSWORD=automation_qa_password \
poetry run pytest tests/database -m "database and not integration" -v
```

Same test files, same command shape — only the `AUTOMATION_DB_*` environment
variables change. See
[DatabaseConfiguration.md](DatabaseConfiguration.md) for every dialect
(including Oracle/SQL Server) and for encrypted-credential setup.

### Switching validation mode (hybrid tests)

```bash
AUTOMATION_VALIDATION_MODE=ui_only poetry run pytest tests/database/integration -m hybrid -v
AUTOMATION_VALIDATION_MODE=ui_api_database poetry run pytest tests/database/integration -m hybrid -v
```

See [HybridValidation.md](HybridValidation.md) — `tests/database/
integration/test_hybrid_validation_facade.py` is parametrized across all
four modes in a single test, so `-k` filtering by mode isn't usually
necessary; it's shown here for pointing an ad hoc run at one mode.

### Docker

```bash
docker compose up -d postgres mysql
docker compose build
docker compose run --rm database-tests    # tests/database against postgres, in-container
docker compose run --rm hybrid-tests      # tests/database/integration against SQLite, in-container
```

### CI

`.github/workflows/ci.yml`'s `test-database` job matrixes the same suite
over `sqlite`/`postgresql`/`mysql` (the latter two via GitHub Actions
service containers); `test-hybrid` runs the UI+API+DB integration suite.
The `docker` job additionally verifies `tests/database/smoke` runs inside
the built image. See that file for the exact steps.

### Debugging a failing database test

1. `logs/execution.log` has every SQL statement, params, execution time, and
   transaction event via `AuditLogger` — same correlation-by-timestamp
   approach as the API layer's request log.
2. Allure attaches the SQL, a JSON telemetry summary (timing/rowcount/
   database/environment), and (capped) returned rows for every executed
   statement, plus a human-readable diff for any `DataComparator`/validator
   comparison — `allure serve reports/allure-results`.
3. If a test passes against SQLite but fails against Postgres/MySQL, it's
   very likely relying on SQLite-only behavior (autoincrement-on-omitted-id,
   or a leftover table from a prior run) — see
   [DatabaseBestPractices.md](DatabaseBestPractices.md)'s "Write
   dialect-portable DDL" section, which documents exactly this failure mode
   from this milestone's own verification.
4. A hybrid test failing on the API leg with a `429` from dummyjson.com is
   the public sandbox's rate limit, not a framework bug — wait a few seconds
   and re-run just that test.

## Test Data Management Suite

### Local

```bash
poetry install --no-root
cp .env.example .env

# All TDM tests — unit (no DB/network) + integration (real SQLite + real API)
poetry run pytest tests/testdata -v

# Just the unit layer — generators, builders, factories, scenarios,
# providers, datasets, validators, masking, synthetic, importers/exporters, cache
poetry run pytest tests/testdata/unit -v

# Just the integration layer — seed/cleanup + fixtures against a real DB,
# and the hybrid TDM->UI/API/DB flow (needs Playwright browsers installed)
poetry run python -m playwright install chromium
poetry run pytest tests/testdata/integration -v
```

### What's live vs. offline

- `tests/testdata/unit/` — no database or network required; pure object
  construction, file I/O against `data/testdata/`, and in-memory logic.
- `tests/testdata/integration/` — hits a real database (SQLite by default,
  same `AUTOMATION_DB_*` override as [DatabaseConfiguration.md](DatabaseConfiguration.md)
  works here too) and, for the hybrid flow test specifically, real
  the-internet.herokuapp.com (UI) and dummyjson.com (API) calls.

### Docker

```bash
docker compose build
docker compose run --rm automation pytest tests/testdata/unit -v
```

The unit suite needs nothing the image doesn't already have. For the
integration suite inside Docker, see the `test-testdata` CI job in
`.github/workflows/ci.yml` for the exact database wiring.

### CI

`.github/workflows/ci.yml`'s `test-testdata` job runs the full
`tests/testdata` suite (unit + integration, SQLite-backed) and additionally
validates that every `data/testdata/` JSON/YAML file this milestone added
is well-formed (dataset validation), that a full seed-then-cleanup round
trip leaves zero rows behind (cleanup verification), and that
`SeedManager`/`ScenarioLibrary` seeding still works end-to-end (seed
verification) — see that file for the exact steps.

### Debugging a failing test-data test

1. A builder/factory test failing usually means a default-generation
   change broke an implicit assumption elsewhere (e.g. a scenario assuming
   a specific field's default) — check
   [BuilderPattern.md](BuilderPattern.md)'s "lazy, not eager" defaults
   section for how `build()` resolves fields.
2. A scenario test failing on referential consistency
   (`test_scenarios.py`) means a new/edited `ScenarioLibrary` method didn't
   thread an ID correctly between entities — see
   [ScenarioLibrary.md](ScenarioLibrary.md).
3. A cleanup test failing to confirm deletion usually means a new entity
   type was added to `DatabaseSeeder`'s repository map but not
   `DatabaseCleanupService`'s (or vice versa) — see
   [CleanupStrategy.md](CleanupStrategy.md).
