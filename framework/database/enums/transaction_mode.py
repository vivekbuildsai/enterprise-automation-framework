from enum import StrEnum


class TransactionMode(StrEnum):
    """How `TransactionManager` should conclude a unit of work."""

    COMMIT = "commit"
    ROLLBACK = "rollback"
    READ_ONLY = "read_only"


class IsolationLevel(StrEnum):
    """SQLAlchemy-recognized isolation level names, exposed here so callers
    import from the database layer instead of stringly-typing it inline.
    Not every dialect supports every level (e.g. SQLite ignores most of
    these) — `ConnectionFactory` passes it straight through to SQLAlchemy,
    which raises a clear error for an unsupported combination.
    """

    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"
    AUTOCOMMIT = "AUTOCOMMIT"
