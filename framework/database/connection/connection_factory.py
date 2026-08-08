from __future__ import annotations

from sqlalchemy import URL
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from framework.config.models import DatabaseConfig
from framework.database.constants import DbDefaults
from framework.database.drivers import ensure_driver_installed
from framework.database.enums import DbDialect
from framework.database.exceptions import DatabaseConnectionError
from framework.database.utilities.secrets import CredentialResolver
from framework.logger import get_logger

try:  # pragma: no cover - import-time only, exercised via create_engine
    from sqlalchemy import create_engine as _sa_create_engine
except ImportError as exc:  # pragma: no cover
    raise DatabaseConnectionError("SQLAlchemy is required for framework.database") from exc

_logger = get_logger("ConnectionFactory")

_IN_MEMORY_SENTINELS = ("", ":memory:")


class ConnectionFactory:
    """Turns a `DatabaseConfig` into a live SQLAlchemy `Engine`.

    This is the single place that knows how to translate `dialect` +
    connection fields into a real connection — everything above it
    (`DatabaseManager`, repositories, tests) works against a plain
    SQLAlchemy `Engine`/`Connection`, so switching Oracle -> PostgreSQL ->
    SQLite is a config change here, never a code change anywhere else.
    """

    @staticmethod
    def build_url(config: DatabaseConfig, *, resolved_password: str) -> URL:
        driver_info = ensure_driver_installed(config.dialect)

        if config.dialect is DbDialect.SQLITE:
            # SQLite has no host/port/user/password — `database` is either a
            # filesystem path or ":memory:"/"" for an in-memory database.
            database = config.database if config.database else ":memory:"
            return URL.create(drivername=driver_info.drivername, database=database)

        return URL.create(
            drivername=driver_info.drivername,
            username=config.username or None,
            password=resolved_password or None,
            host=config.host or None,
            port=config.port or driver_info.default_port,
            database=config.database or None,
        )

    @staticmethod
    def create_engine(config: DatabaseConfig, *, echo: bool = False) -> Engine:
        """Builds and returns a new `Engine` for `config`. Does not cache —
        callers that want one engine per process (the normal case) should go
        through `DatabaseManager`, which owns the cache and lazy-loading
        behaviour; this method is the low-level, cache-free primitive it's
        built on (and what unit tests exercise directly).
        """
        password = CredentialResolver.resolve_password(config)
        url = ConnectionFactory.build_url(config, resolved_password=password)

        is_in_memory_sqlite = config.dialect is DbDialect.SQLITE and (
            config.database in _IN_MEMORY_SENTINELS
        )

        if is_in_memory_sqlite:
            # In-memory SQLite is per-connection by default, which would make
            # every `engine.connect()` see an empty, freshly-created database.
            # StaticPool pins the engine to a single physical connection so
            # schema/data set up on one connection is visible on the next.
            engine = _sa_create_engine(
                url,
                echo=echo,
                future=True,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False, **config.connect_args},
            )
        elif config.dialect is DbDialect.SQLITE:
            engine = _sa_create_engine(
                url,
                echo=echo,
                future=True,
                connect_args={"check_same_thread": False, **config.connect_args},
            )
        else:
            engine = _sa_create_engine(
                url,
                echo=echo,
                future=True,
                pool_size=config.pool_size or DbDefaults.POOL_SIZE,
                max_overflow=config.pool_max_overflow or DbDefaults.POOL_MAX_OVERFLOW,
                pool_timeout=config.pool_timeout_seconds or DbDefaults.POOL_TIMEOUT_SECONDS,
                pool_recycle=config.pool_recycle_seconds or DbDefaults.POOL_RECYCLE_SECONDS,
                pool_pre_ping=True,
                connect_args=config.connect_args,
            )

        _logger.info(
            f"Created engine for dialect={config.dialect.value} "
            f"database={config.database or ':memory:'} host={config.host or 'n/a'}"
        )
        return engine
