# Database Configuration

How to point the database layer at a different dialect/server — every
example below is a **configuration change only**; no code in
`framework/database/` or any test changes.

## The config shape

```yaml
# config/environments/<env>.yaml
database:
  subscriber_db:                      # a "db_key" — the name a test's `db_key`
    enabled: true                     #   fixture points at (default: "subscriber_db")
    dialect: "${AUTOMATION_DB_DIALECT:-sqlite}"
    host: "${AUTOMATION_DB_HOST:-}"
    port: "${AUTOMATION_DB_PORT:-0}"         # 0 = fall back to the dialect's default port
    database: "${AUTOMATION_DB_NAME:-:memory:}"
    username: "${AUTOMATION_DB_USER:-}"
    password: "${AUTOMATION_DB_PASSWORD:-}"
    pool_size: 5
```

`${VAR:-default}` is resolved by `framework.config.settings` at load time —
secrets never live in the YAML file itself, only the *name* of the
environment variable that supplies them (see
[Authentication.md](Authentication.md) for the same pattern on the API
side). `dev.yaml` defaults to SQLite in-memory specifically so the whole
suite runs with zero setup; every other environment (`qa`/`uat`/`preprod`/
`production`) has a fixed real dialect already configured (PostgreSQL,
PostgreSQL, Oracle, Oracle respectively) as a working example of one
environment per dialect.

## Switching dialects locally

Every example below runs the exact same command —
`pytest tests/database -m "database and not integration"` — only the
environment variables change.

### SQLite (default — zero setup)

```bash
poetry run pytest tests/database -m "database and not integration"
```

### PostgreSQL

```bash
docker compose up -d postgres        # postgres:16-alpine, see docker-compose.yml

AUTOMATION_DB_DIALECT=postgresql \
AUTOMATION_DB_HOST=localhost \
AUTOMATION_DB_PORT=5432 \
AUTOMATION_DB_NAME=sample_app \
AUTOMATION_DB_USER=automation_qa \
AUTOMATION_DB_PASSWORD=automation_qa_password \
poetry run pytest tests/database -m "database and not integration"
```

### MySQL

```bash
docker compose up -d mysql           # mysql:8.4

AUTOMATION_DB_DIALECT=mysql \
AUTOMATION_DB_HOST=localhost \
AUTOMATION_DB_PORT=3306 \
AUTOMATION_DB_NAME=sample_app \
AUTOMATION_DB_USER=automation_qa \
AUTOMATION_DB_PASSWORD=automation_qa_password \
poetry run pytest tests/database -m "database and not integration"
```

Both of the above were run against real containers during this milestone's
verification — see [DatabaseFramework.md](DatabaseFramework.md#verified-against).

### Oracle / SQL Server

```bash
poetry install --with oracle      # installs oracledb (thin mode, no Instant Client needed)
# or: poetry install --with mssql   # installs pyodbc (needs a system ODBC driver)

docker compose --profile oracle up -d oracle-xe   # gvenzl/oracle-xe:21-slim (optional, large image)

AUTOMATION_DB_DIALECT=oracle \
AUTOMATION_DB_HOST=localhost \
AUTOMATION_DB_PORT=1521 \
AUTOMATION_DB_NAME=XEPDB1 \
AUTOMATION_DB_USER=automation_qa \
AUTOMATION_DB_PASSWORD=automation_qa_password \
poetry run pytest tests/database -m "database and not integration"
```

Not run against a live server in this environment (no Oracle/SQL Server
license/container available) — `ConnectionFactory`/`dialect_registry`'s
Oracle/SQL Server driver-name mapping is unit-tested
(`test_connection_factory.py`), and `ensure_driver_installed` raises a clear
`DriverNotInstalledError` naming the exact `poetry install --with ...` group
if the driver isn't installed, rather than a bare import error.

## Encrypted credentials

`DatabaseConfig.encrypted_password` (checked before `password`) lets a
Fernet ciphertext live in a committed YAML file instead of a plaintext
secret:

```bash
python -c "
from framework.database.utilities.secrets import CredentialResolver as C
key = C.generate_key()
print('AUTOMATION_DB_SECRET_KEY=' + key)
print('encrypted_password:', C.encrypt('the-real-password', key))
"
```

```yaml
database:
  subscriber_db:
    encrypted_password: "gAAAAA...."   # from the command above
    # password: left empty — encrypted_password takes priority
```

`AUTOMATION_DB_SECRET_KEY` (the decryption key) still only ever lives in the
environment/secrets manager — never in a tracked file. Missing or wrong key
raises `DatabaseConnectionError` with an actionable message rather than
silently falling back to plaintext.

## `.env` reference

```bash
AUTOMATION_VALIDATION_MODE=ui_api_database   # ui_only | ui_api | ui_database | ui_api_database
AUTOMATION_DB_DIALECT=sqlite                 # postgresql | mysql | oracle | mssql | sqlite
AUTOMATION_DB_HOST=
AUTOMATION_DB_PORT=0
AUTOMATION_DB_NAME=:memory:
AUTOMATION_DB_USER=
AUTOMATION_DB_PASSWORD=
AUTOMATION_DB_SECRET_KEY=                    # only if using encrypted_password
```

See [.env.example](../.env.example) for the full, current list.

## CI

`.github/workflows/ci.yml`'s `test-database` job runs this exact same suite
three times — `sqlite`, `postgresql`, `mysql` — as a matrix, with real
Postgres/MySQL service containers, purely by setting these same environment
variables per matrix entry. See that file for the exact config.
