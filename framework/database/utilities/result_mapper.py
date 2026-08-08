from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

from sqlalchemy.engine import CursorResult

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Everything about one executed statement — exactly the fields
    `docs/DatabaseFramework.md`'s reporting section requires attached to
    Allure: the SQL, how long it took, how many rows came back, and which
    database it ran against.
    """

    sql: str
    params: dict[str, Any]
    rows: list[dict[str, Any]]
    rowcount: int
    elapsed_ms: float
    database: str
    dialect: str
    error: str | None = field(default=None)

    @property
    def succeeded(self) -> bool:
        return self.error is None


class ResultMapper:
    """Converts SQLAlchemy result rows into plain data structures or
    caller-supplied model types. Kept separate from `QueryExecutor` so
    mapping logic (row -> dict, rows -> dataclass instances) is unit
    testable against plain data without spinning up a real connection.
    """

    @staticmethod
    def to_dicts(cursor_result: CursorResult[Any]) -> list[dict[str, Any]]:
        return [dict(row._mapping) for row in cursor_result]

    @staticmethod
    def to_model(row: dict[str, Any], model: type[T]) -> T:
        """Maps one row's dict onto `model`, a dataclass (or any callable
        accepting the row's columns as keyword arguments). Column names must
        match the model's field names exactly — repositories are expected to
        `SELECT ... AS <field_name>` when a query's column names don't
        already match, keeping the mismatch visible in the SQL rather than
        hidden behind implicit renaming here.
        """
        return model(**row)

    @staticmethod
    def to_models(rows: list[dict[str, Any]], model: type[T]) -> list[T]:
        return [ResultMapper.to_model(row, model) for row in rows]

    @staticmethod
    def single_or_none(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        return rows[0] if rows else None
