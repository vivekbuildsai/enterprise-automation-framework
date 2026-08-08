from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from framework.config.models import DatabaseConfig, EnvironmentSettings
from framework.database.connection.connection_factory import ConnectionFactory
from framework.database.connection.connection_pool import ConnectionPoolManager, PoolStats
from framework.database.exceptions import DatabaseConnectionError
from framework.exceptions import ConfigurationError
from framework.logger import get_logger

_logger = get_logger("DatabaseManager")


class DatabaseManager:
    """Top-level entry point to the database layer. Owns one `Engine` per
    `db_key` (a name in `settings.database`, e.g. `"subscriber_db"`),
    created lazily on first use and cached for the lifetime of this
    `DatabaseManager` — the same "one engine per target, reused" pattern
    `ApiClient` follows for HTTP connections.

    Everything downstream (`QueryExecutor`, repositories, `UnitOfWork`) is
    handed a `Connection` from here rather than reaching into SQLAlchemy or
    `settings.database` directly, so this is the one place that has to
    change if engine lifecycle policy ever changes.
    """

    def __init__(self, settings: EnvironmentSettings, *, echo: bool = False) -> None:
        self._settings = settings
        self._echo = echo
        self._engines: dict[str, Engine] = {}
        self._pools: dict[str, ConnectionPoolManager] = {}

    def config_for(self, db_key: str) -> DatabaseConfig:
        try:
            return self._settings.database[db_key]
        except KeyError as exc:
            env_name = self._settings.environment.value
            raise ConfigurationError(
                f"No database config for '{db_key}' in the '{env_name}' environment — "
                f"add it under `database:` in config/environments/{env_name}.yaml"
            ) from exc

    def get_engine(self, db_key: str) -> Engine:
        """Lazily creates (on first call) and caches the `Engine` for
        `db_key`. Safe to call repeatedly — subsequent calls are a dict
        lookup, not a new connection.
        """
        if db_key not in self._engines:
            config = self.config_for(db_key)
            engine = ConnectionFactory.create_engine(config, echo=self._echo)
            self._engines[db_key] = engine
            self._pools[db_key] = ConnectionPoolManager(engine)
        return self._engines[db_key]

    def pool_stats(self, db_key: str) -> PoolStats:
        self.get_engine(db_key)  # ensure it's created so a pool exists
        return self._pools[db_key].stats()

    @contextmanager
    def connection(self, db_key: str) -> Iterator[Connection]:
        """A raw connection with no transaction opened — callers that need
        explicit transaction control should use `TransactionManager` instead
        (see `framework.database.utilities.transaction_manager`), which
        wraps this same connection.
        """
        engine = self.get_engine(db_key)
        try:
            with engine.connect() as conn:
                yield conn
        except SQLAlchemyError as exc:
            raise DatabaseConnectionError(f"Failed to connect to '{db_key}': {exc}") from exc

    def health_check(self, db_key: str) -> bool:
        """Executes `SELECT 1` against `db_key` and returns whether it
        succeeded. Never raises — a health check that can itself fail with
        an unhandled exception isn't a useful health check.
        """
        try:
            with self.connection(db_key) as conn:
                conn.execute(text("SELECT 1"))
            return True
        except (ConfigurationError, DatabaseConnectionError, SQLAlchemyError) as exc:
            _logger.warning(f"Health check failed for '{db_key}': {exc}")
            return False

    def dispose(self, db_key: str) -> None:
        if db_key in self._pools:
            self._pools[db_key].dispose()
        self._engines.pop(db_key, None)
        self._pools.pop(db_key, None)

    def dispose_all(self) -> None:
        for db_key in list(self._engines):
            self.dispose(db_key)
