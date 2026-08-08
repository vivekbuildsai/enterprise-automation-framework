from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Connection

from framework.database.enums import TransactionMode
from framework.database.utilities.transaction_manager import TransactionManager


class RollbackManager:
    """Wraps `TransactionManager` for the "never commit, always rollback"
    cleanup style: a test runs entirely inside a transaction that's rolled
    back at the end regardless of outcome, so no explicit per-row delete is
    ever needed.

    Prefer `DatabaseCleanupService` when a test needs to see its own
    committed writes from a second connection (e.g. verifying via a real
    API call that hits the DB independently); prefer this when the test
    never needs that — it's cheaper and can't leak data on a crash mid-test.
    """

    def __init__(self, connection: Connection, *, db_key: str = "default") -> None:
        self._transaction_manager = TransactionManager(connection, db_key=db_key)

    @contextmanager
    def rollback_scope(self) -> Iterator[Connection]:
        with self._transaction_manager.transaction(mode=TransactionMode.ROLLBACK) as conn:
            yield conn
