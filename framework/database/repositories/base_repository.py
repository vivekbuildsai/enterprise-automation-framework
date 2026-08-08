from __future__ import annotations

from typing import Any, Generic, TypeVar

from framework.database.exceptions import RepositoryError
from framework.database.utilities.query_executor import QueryExecutor
from framework.database.utilities.result_mapper import ResultMapper

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Common row <-> model mapping shared by every domain repository.
    A domain repository sets `model` to its dataclass and otherwise only
    declares domain-specific query methods — the repeated "map this row (or
    these rows) onto my model" logic lives here once.

    Deliberately does not hardcode `get_by_id`/`find_all` here: different
    domains key on different columns (`subscriber_id` vs `zone_id` vs
    `config_key`), so each repository declares its own — but they all build
    on `_map_one`/`_map_many`/`require_one`.
    """

    model: type[T]

    def __init__(self, executor: QueryExecutor) -> None:
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
