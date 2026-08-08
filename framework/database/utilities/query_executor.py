from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.elements import TextClause

from framework.database.audit import AuditLogger
from framework.database.constants import DbDefaults
from framework.database.exceptions import DatabaseQueryError
from framework.database.telemetry import attach_query_telemetry
from framework.database.utilities.result_mapper import ExecutionResult, ResultMapper


class QueryExecutor:
    """The single place every SQL statement in this framework passes
    through: it times execution, maps rows via `ResultMapper`, logs to the
    audit trail, and attaches telemetry to Allure. Repositories call this
    instead of `Connection.execute()` directly — the same relationship
    `ApiClient` has to raw `httpx` calls.
    """

    def __init__(
        self,
        connection: Connection,
        *,
        db_key: str,
        dialect: str,
        environment: str = "",
        slow_query_threshold_ms: float = DbDefaults.SLOW_QUERY_THRESHOLD_MS,
    ) -> None:
        self._connection = connection
        self._db_key = db_key
        self._dialect = dialect
        self._environment = environment
        self._slow_query_threshold_ms = slow_query_threshold_ms

    def execute(
        self, sql: str | TextClause, params: dict[str, Any] | None = None
    ) -> ExecutionResult:
        stmt = text(sql) if isinstance(sql, str) else sql
        bind_params = params or {}
        start = time.perf_counter()

        try:
            cursor_result = self._connection.execute(stmt, bind_params)
        except SQLAlchemyError as exc:
            AuditLogger.query_failed(self._db_key, str(stmt), bind_params, str(exc))
            raise DatabaseQueryError(
                f"Query failed against '{self._db_key}': {exc}\nSQL: {stmt}\nParams: {bind_params}"
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        if cursor_result.returns_rows:
            rows = ResultMapper.to_dicts(cursor_result)
            rowcount = len(rows)
        else:
            rows = []
            rowcount = cursor_result.rowcount if cursor_result.rowcount != -1 else 0

        result = ExecutionResult(
            sql=str(stmt),
            params=bind_params,
            rows=rows,
            rowcount=rowcount,
            elapsed_ms=elapsed_ms,
            database=self._db_key,
            dialect=self._dialect,
        )
        AuditLogger.query_executed(result)
        if elapsed_ms > self._slow_query_threshold_ms:
            AuditLogger.slow_query(result, threshold_ms=self._slow_query_threshold_ms)
        attach_query_telemetry(result, environment=self._environment)
        return result

    def fetch_all(
        self, sql: str | TextClause, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return self.execute(sql, params).rows

    def fetch_one(
        self, sql: str | TextClause, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        return ResultMapper.single_or_none(self.fetch_all(sql, params))

    def execute_write(self, sql: str | TextClause, params: dict[str, Any] | None = None) -> int:
        """For INSERT/UPDATE/DELETE — returns affected-row count instead of
        the full `ExecutionResult`, for callers that only care about the
        write outcome.
        """
        return self.execute(sql, params).rowcount
