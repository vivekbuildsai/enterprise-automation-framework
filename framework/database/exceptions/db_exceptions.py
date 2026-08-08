from __future__ import annotations

from framework.exceptions import DatabaseConnectionError, DatabaseQueryError, ValidationError


class DriverNotInstalledError(DatabaseConnectionError):
    """Raised when a dialect is configured but its SQLAlchemy driver package
    isn't installed — carries the pip package name so the failure is
    actionable instead of a bare `ModuleNotFoundError` several frames deep
    inside SQLAlchemy.
    """


class UnsupportedDialectError(DatabaseConnectionError):
    """Raised when `DatabaseConfig.dialect` isn't one of `DbDialect`'s
    supported values.
    """


class TransactionError(DatabaseQueryError):
    """Raised when a transaction cannot be started, committed, rolled back,
    or nested (e.g. requesting a nested transaction against a dialect/driver
    that doesn't support `SAVEPOINT`).
    """


class RepositoryError(DatabaseQueryError):
    """Raised by repository methods when a query succeeds at the SQL level
    but the result can't satisfy the caller's contract (e.g. `get_by_id`
    finding zero or more than one row).
    """


class UnitOfWorkError(DatabaseQueryError):
    """Raised when a Unit of Work fails to commit or coordinate its
    registered repositories.
    """


class DataComparisonError(ValidationError):
    """Raised by `DataComparator`/business validators when a cross-layer
    (UI/API/DB) comparison fails — carries a human-readable diff in the
    message so a CI failure is diagnosable without re-running locally.
    """


class SeedDataError(DatabaseQueryError):
    """Raised when database seed or cleanup data cannot be applied."""
