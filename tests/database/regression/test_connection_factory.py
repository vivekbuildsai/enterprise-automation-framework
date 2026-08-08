from __future__ import annotations

import pytest

from framework.config.models import DatabaseConfig
from framework.database.connection import ConnectionFactory
from framework.database.drivers import dialect_registry
from framework.database.enums import DbDialect
from framework.database.exceptions import DriverNotInstalledError, UnsupportedDialectError

pytestmark = [pytest.mark.regression, pytest.mark.database]


@pytest.mark.parametrize(
    ("dialect", "expected_drivername"),
    [
        (DbDialect.POSTGRESQL, "postgresql+psycopg2"),
        (DbDialect.MYSQL, "mysql+pymysql"),
        (DbDialect.ORACLE, "oracle+oracledb"),
        (DbDialect.MSSQL, "mssql+pyodbc"),
        (DbDialect.SQLITE, "sqlite"),
    ],
)
def test_dialect_registry_maps_every_dialect_to_its_driver(
    dialect: DbDialect, expected_drivername: str
) -> None:
    """Driver-name mapping is dialect-registry-level and doesn't require the
    driver package to actually be installed (see `resolve` vs
    `ensure_driver_installed`) — Oracle/SQL Server drivers are optional
    poetry groups not installed in the base test environment, so this
    covers all 5 dialects' mapping without needing them installed.
    """
    assert dialect_registry.resolve(dialect).drivername == expected_drivername


@pytest.mark.parametrize(
    ("dialect", "expected_drivername"),
    [
        (DbDialect.POSTGRESQL, "postgresql+psycopg2"),
        (DbDialect.MYSQL, "mysql+pymysql"),
        (DbDialect.SQLITE, "sqlite"),
    ],
)
def test_build_url_selects_correct_driver_for_installed_dialects(
    dialect: DbDialect, expected_drivername: str
) -> None:
    """`build_url` additionally enforces the driver is installed
    (`ensure_driver_installed`) — only exercised here for dialects whose
    driver is part of the base install (Oracle/SQL Server are covered by
    `test_ensure_driver_installed_raises_actionable_error_when_missing`
    below instead, via a forced-missing simulation).
    """
    config = DatabaseConfig(
        dialect=dialect, host="dbhost", port=0, database="mydb", username="u", password="p"
    )
    url = ConnectionFactory.build_url(config, resolved_password="p")
    assert url.drivername == expected_drivername


def test_sqlite_in_memory_url_ignores_host_and_credentials() -> None:
    config = DatabaseConfig(dialect=DbDialect.SQLITE, database=":memory:", host="ignored")
    url = ConnectionFactory.build_url(config, resolved_password="ignored")
    assert url.database == ":memory:"
    assert url.host is None


def test_missing_port_falls_back_to_dialect_default() -> None:
    config = DatabaseConfig(
        dialect=DbDialect.MYSQL, host="dbhost", port=0, database="mydb", username="u", password="p"
    )
    url = ConnectionFactory.build_url(config, resolved_password="p")
    assert url.port == 3306


def test_explicit_port_overrides_dialect_default() -> None:
    config = DatabaseConfig(
        dialect=DbDialect.MYSQL,
        host="dbhost",
        port=13306,
        database="mydb",
        username="u",
        password="p",
    )
    url = ConnectionFactory.build_url(config, resolved_password="p")
    assert url.port == 13306


def test_create_engine_sqlite_in_memory_is_queryable() -> None:
    config = DatabaseConfig(dialect=DbDialect.SQLITE, database=":memory:")
    engine = ConnectionFactory.create_engine(config)
    try:
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT 1").scalar() == 1
    finally:
        engine.dispose()


def test_resolve_raises_for_unsupported_dialect() -> None:
    with pytest.raises(UnsupportedDialectError):
        dialect_registry.resolve("not_a_real_dialect")  # type: ignore[arg-type]


def test_ensure_driver_installed_raises_actionable_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dialect_registry.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(DriverNotInstalledError, match="oracledb"):
        dialect_registry.ensure_driver_installed(DbDialect.ORACLE)
