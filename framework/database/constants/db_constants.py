from __future__ import annotations

from types import MappingProxyType

from framework.database.enums import DbDialect


class DialectDriverInfo:
    """Everything `ConnectionFactory` needs to turn a `DbDialect` into a
    SQLAlchemy connection URL: the SQLAlchemy driver name suffix, the
    conventional default port, and the pip package that must be installed
    for that driver (used to raise an actionable error instead of a bare
    `ModuleNotFoundError` when an optional driver group wasn't installed).
    """

    __slots__ = ("drivername", "default_port", "pip_package")

    def __init__(self, drivername: str, default_port: int | None, pip_package: str) -> None:
        self.drivername = drivername
        self.default_port = default_port
        self.pip_package = pip_package


DIALECT_DRIVERS: MappingProxyType[DbDialect, DialectDriverInfo] = MappingProxyType(
    {
        DbDialect.POSTGRESQL: DialectDriverInfo("postgresql+psycopg2", 5432, "psycopg2-binary"),
        DbDialect.MYSQL: DialectDriverInfo("mysql+pymysql", 3306, "pymysql"),
        DbDialect.ORACLE: DialectDriverInfo("oracle+oracledb", 1521, "oracledb"),
        DbDialect.MSSQL: DialectDriverInfo("mssql+pyodbc", 1433, "pyodbc"),
        DbDialect.SQLITE: DialectDriverInfo("sqlite", None, "(stdlib — no driver needed)"),
    }
)


class DbDefaults:
    """Framework-wide defaults for the database layer. Any of these can be
    overridden per-environment via `DatabaseConfig` — these are only the
    fallback when a value isn't set in `config/environments/<env>.yaml`.
    """

    POOL_SIZE = 5
    POOL_MAX_OVERFLOW = 10
    POOL_TIMEOUT_SECONDS = 10
    POOL_RECYCLE_SECONDS = 1800
    QUERY_TIMEOUT_SECONDS = 30
    SLOW_QUERY_THRESHOLD_MS = 500
    CONNECT_RETRY_ATTEMPTS = 3
    CONNECT_RETRY_WAIT_SECONDS = 2.0
