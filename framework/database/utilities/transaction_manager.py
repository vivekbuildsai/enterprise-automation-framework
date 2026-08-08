from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Connection

from framework.database.audit import AuditLogger
from framework.database.enums import TransactionMode
from framework.database.exceptions import TransactionError


class TransactionManager:
    """Wraps a `Connection`'s transaction lifecycle: commit / rollback /
    read-only / nested (`SAVEPOINT`). One instance per connection — acquire
    a fresh connection from `DatabaseManager.connection()` and wrap it here
    for the lifetime of that unit of work.
    """

    def __init__(self, connection: Connection, *, db_key: str = "default") -> None:
        self._connection = connection
        self._db_key = db_key

    @contextmanager
    def transaction(
        self, *, mode: TransactionMode = TransactionMode.COMMIT
    ) -> Iterator[Connection]:
        """Top-level transaction.

        - `COMMIT` (default): commits on clean exit, rolls back on exception.
        - `ROLLBACK`: always rolls back on exit, even without an exception —
          for tests that must leave zero trace in the database.
        - `READ_ONLY`: behaves like `ROLLBACK` but documents *intent* (no
          writes expected) rather than "we're discarding writes on purpose".
        """
        AuditLogger.transaction_started(self._db_key)
        outer = self._connection.begin()
        try:
            yield self._connection
        except Exception as exc:
            outer.rollback()
            AuditLogger.transaction_rolled_back(self._db_key, reason=str(exc))
            raise
        else:
            if mode is TransactionMode.COMMIT:
                outer.commit()
                AuditLogger.transaction_committed(self._db_key)
            else:
                outer.rollback()
                AuditLogger.transaction_rolled_back(self._db_key, reason=f"mode={mode.value}")

    @contextmanager
    def nested_transaction(self) -> Iterator[Connection]:
        """A `SAVEPOINT` nested inside an already-open transaction — lets a
        block of code attempt writes and roll back just that portion without
        aborting the enclosing transaction. Must be called from inside
        `transaction()`; raises `TransactionError` otherwise.
        """
        if not self._connection.in_transaction():
            raise TransactionError(
                f"nested_transaction() requires an already-open transaction on "
                f"'{self._db_key}' — call it from inside transaction()."
            )
        AuditLogger.transaction_started(self._db_key, nested=True)
        savepoint = self._connection.begin_nested()
        try:
            yield self._connection
        except Exception as exc:
            savepoint.rollback()
            AuditLogger.transaction_rolled_back(self._db_key, reason=f"savepoint: {exc}")
            raise
        else:
            savepoint.commit()
            AuditLogger.transaction_committed(self._db_key)
