from __future__ import annotations

from typing import Any

from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError
from clickhouse_connect.driver.query import QueryResult

from framework.database.exceptions import DatabaseQueryError
from framework.exceptions import RetryExhaustedError
from framework.logger import get_logger
from framework.retry import retry_on

_logger = get_logger("ClickHouseQueryExecutor")


class ClickHouseQueryExecutor:
    """Runs queries against a ClickHouse `Client` with retry (via the
    framework's shared `retry_on`) and exception translation — the
    ClickHouse-layer equivalent of
    `framework.database.utilities.query_executor.QueryExecutor`.

    `_run` is the retried unit and deliberately lets `ClickHouseError`
    propagate un-caught — catching and translating it *inside* the retried
    function would swallow the exception the retry decorator is watching
    for, silently defeating the retry. Translation to `DatabaseQueryError`
    happens in the public methods, once retries are exhausted (or on a
    non-retried failure).
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    @retry_on(ClickHouseError)
    def _run(self, sql: str, parameters: dict[str, Any] | None) -> QueryResult:
        _logger.debug(f"Executing ClickHouse query: {sql!r}")
        return self._client.query(sql, parameters=parameters)

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Rows as header-keyed dicts — the common case for "does this row
        exist with these values" assertions.
        """
        try:
            result = self._run(sql, parameters)
        except (ClickHouseError, RetryExhaustedError) as exc:
            raise DatabaseQueryError(f"ClickHouse query failed: {sql!r}: {exc}") from exc
        return list(result.named_results())

    def query_rows(
        self, sql: str, parameters: dict[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        try:
            result = self._run(sql, parameters)
        except (ClickHouseError, RetryExhaustedError) as exc:
            raise DatabaseQueryError(f"ClickHouse query failed: {sql!r}: {exc}") from exc
        return [tuple(row) for row in result.result_rows]

    def query_single(
        self, sql: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        rows = self.query(sql, parameters)
        if not rows:
            return None
        if len(rows) > 1:
            raise DatabaseQueryError(f"Expected exactly one row, got {len(rows)}: {sql!r}")
        return rows[0]
