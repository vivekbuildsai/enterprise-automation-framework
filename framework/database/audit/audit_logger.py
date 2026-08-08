from __future__ import annotations

from framework.database.utilities.result_mapper import ExecutionResult
from framework.logger import get_logger

_logger = get_logger("DatabaseAudit")


class AuditLogger:
    """Structured, loguru-backed audit trail for everything the database
    layer does — connections, SQL statements, execution time, affected rows,
    failures, retries, and transactions — independent of Allure (which is
    per-test-report; this is the persistent `logs/execution.log` trail used
    for post-hoc incident investigation, per `docs/DatabaseBestPractices.md`).
    """

    @staticmethod
    def connection_opened(db_key: str, *, dialect: str, host: str) -> None:
        _logger.info(f"DB connection opened | db={db_key} dialect={dialect} host={host or 'n/a'}")

    @staticmethod
    def connection_closed(db_key: str) -> None:
        _logger.info(f"DB connection closed | db={db_key}")

    @staticmethod
    def query_executed(result: ExecutionResult) -> None:
        _logger.debug(
            f"DB query | db={result.database} dialect={result.dialect} "
            f"rows={result.rowcount} elapsed_ms={result.elapsed_ms:.2f} | sql={result.sql} "
            f"params={result.params}"
        )

    @staticmethod
    def query_failed(db_key: str, sql: str, params: dict[str, object], error: str) -> None:
        _logger.error(f"DB query failed | db={db_key} | sql={sql} params={params} | error={error}")

    @staticmethod
    def slow_query(result: ExecutionResult, *, threshold_ms: float) -> None:
        _logger.warning(
            f"Slow DB query | db={result.database} elapsed_ms={result.elapsed_ms:.2f} "
            f"(threshold={threshold_ms:.0f}ms) | sql={result.sql}"
        )

    @staticmethod
    def transaction_started(db_key: str, *, nested: bool = False) -> None:
        kind = "nested (SAVEPOINT)" if nested else "top-level"
        _logger.info(f"DB transaction started | db={db_key} kind={kind}")

    @staticmethod
    def transaction_committed(db_key: str) -> None:
        _logger.info(f"DB transaction committed | db={db_key}")

    @staticmethod
    def transaction_rolled_back(db_key: str, *, reason: str = "") -> None:
        _logger.warning(f"DB transaction rolled back | db={db_key} reason={reason or 'n/a'}")

    @staticmethod
    def retry_attempt(db_key: str, *, attempt: int, max_attempts: int, error: str) -> None:
        _logger.warning(f"DB retry | db={db_key} attempt={attempt}/{max_attempts} error={error}")
