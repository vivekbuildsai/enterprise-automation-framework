from __future__ import annotations

import importlib.util

from framework.database.constants import DIALECT_DRIVERS, DialectDriverInfo
from framework.database.enums import DbDialect
from framework.database.exceptions import DriverNotInstalledError, UnsupportedDialectError

# SQLAlchemy driver suffix -> the actual importable module name to probe for.
_IMPORT_MODULE_BY_DRIVERNAME: dict[str, str] = {
    "postgresql+psycopg2": "psycopg2",
    "mysql+pymysql": "pymysql",
    "oracle+oracledb": "oracledb",
    "mssql+pyodbc": "pyodbc",
    "sqlite": "sqlite3",
}


def resolve(dialect: DbDialect) -> DialectDriverInfo:
    """Look up the SQLAlchemy driver metadata for `dialect`.

    Raises `UnsupportedDialectError` for a dialect this framework doesn't
    know about at all (should be unreachable given `DbDialect` is an enum,
    but config can still hand us a raw string before pydantic validates it).
    """
    try:
        return DIALECT_DRIVERS[dialect]
    except KeyError as exc:
        supported = ", ".join(d.value for d in DbDialect)
        raise UnsupportedDialectError(
            f"'{dialect}' is not a supported dialect. Supported: {supported}"
        ) from exc


def ensure_driver_installed(dialect: DbDialect) -> DialectDriverInfo:
    """Same as `resolve`, but also verifies the underlying driver package is
    importable, raising a `DriverNotInstalledError` that names the exact pip
    package to install (e.g. Oracle/SQL Server drivers are optional poetry
    groups — this is the error a QA engineer sees if they didn't install
    them) instead of a bare `ModuleNotFoundError` raised deep inside
    SQLAlchemy's dialect-loading machinery.
    """
    info = resolve(dialect)
    module_name = _IMPORT_MODULE_BY_DRIVERNAME[info.drivername]
    if importlib.util.find_spec(module_name) is None:
        raise DriverNotInstalledError(
            f"Dialect '{dialect.value}' requires the '{info.pip_package}' package "
            f"(import name '{module_name}'), which is not installed. "
            f"Install it via `poetry install --with {dialect.value}` "
            f"(see pyproject.toml optional dependency groups) or `pip install {info.pip_package}`."
        )
    return info
