from __future__ import annotations

from types import TracebackType
from typing import Any, TypeVar

from sqlalchemy.engine import Connection

from framework.database.connection import DatabaseManager
from framework.database.enums import TransactionMode
from framework.database.exceptions import UnitOfWorkError
from framework.database.repositories.base_repository import BaseRepository
from framework.database.utilities.query_executor import QueryExecutor
from framework.database.utilities.transaction_manager import TransactionManager

R = TypeVar("R", bound=BaseRepository[Any])


class UnitOfWork:
    """Coordinates one or more repositories under a single database
    transaction so their writes commit — or roll back — together.
    Repositories are constructed lazily and cached per `UnitOfWork`
    instance, so a caller only pays for the ones it actually asks for.

    Example::

        with UnitOfWork(db_manager, "subscriber_db") as uow:
            subscribers = uow.repository(SubscriberRepository)
            audit = uow.repository(AuditRepository)
            subscribers.update_status(subscriber_id, "SUSPENDED")
            audit.record(...)
        # both writes commit together, or both roll back on exception
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        db_key: str,
        *,
        mode: TransactionMode = TransactionMode.COMMIT,
        environment: str = "",
    ) -> None:
        self._db_manager = db_manager
        self._db_key = db_key
        self._mode = mode
        self._environment = environment
        self._connection: Connection | None = None
        self._transaction_cm: Any = None
        self._executor: QueryExecutor | None = None
        self._repositories: dict[type[Any], Any] = {}

    def __enter__(self) -> UnitOfWork:
        config = self._db_manager.config_for(self._db_key)
        self._connection = self._db_manager.get_engine(self._db_key).connect()
        transaction_manager = TransactionManager(self._connection, db_key=self._db_key)
        self._transaction_cm = transaction_manager.transaction(mode=self._mode)
        self._transaction_cm.__enter__()
        self._executor = QueryExecutor(
            self._connection,
            db_key=self._db_key,
            dialect=config.dialect.value,
            environment=self._environment,
        )
        return self

    def repository(self, repository_cls: type[R]) -> R:
        if self._executor is None:
            raise UnitOfWorkError(
                "UnitOfWork must be entered (`with UnitOfWork(...) as uow:`) "
                "before requesting a repository."
            )
        if repository_cls not in self._repositories:
            self._repositories[repository_cls] = repository_cls(self._executor)
        return self._repositories[repository_cls]  # type: ignore[no-any-return]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        try:
            suppressed = bool(self._transaction_cm.__exit__(exc_type, exc_val, exc_tb))
        finally:
            if self._connection is not None:
                self._connection.close()
            self._connection = None
            self._executor = None
            self._repositories.clear()
        return suppressed
