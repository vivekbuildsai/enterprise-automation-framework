from __future__ import annotations

from typing import Any, Generic, TypeVar

from framework.database.clickhouse.query_executor import ClickHouseQueryExecutor
from framework.database.exceptions import RepositoryError
from framework.database.utilities.result_mapper import ResultMapper

T = TypeVar("T")


class BaseClickHouseRepository(Generic[T]):
    """ClickHouse-layer counterpart to
    `framework.database.repositories.BaseRepository` — same row <-> model
    mapping (`ResultMapper` only needs plain dicts, nothing SQLAlchemy-
    specific, so it's reused as-is here rather than duplicated), backed by
    `ClickHouseQueryExecutor` instead of the SQLAlchemy `QueryExecutor`.
    """

    model: type[T]

    def __init__(self, executor: ClickHouseQueryExecutor) -> None:
        self._executor = executor

    def _map_one(self, row: dict[str, Any] | None) -> T | None:
        return ResultMapper.to_model(row, self.model) if row is not None else None

    def _map_many(self, rows: list[dict[str, Any]]) -> list[T]:
        return ResultMapper.to_models(rows, self.model)

    def require_one(self, row: dict[str, Any] | None, *, not_found_message: str) -> T:
        mapped = self._map_one(row)
        if mapped is None:
            raise RepositoryError(not_found_message)
        return mapped
