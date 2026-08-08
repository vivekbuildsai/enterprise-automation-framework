from __future__ import annotations

from clickhouse_connect.driver.exceptions import ClickHouseError

from framework.database.clickhouse.client import ClickHouseClient
from framework.database.exceptions import DatabaseConnectionError
from framework.exceptions import ConfigurationError
from framework.logger import get_logger

_logger = get_logger("ClickHouseHealthCheck")


class ClickHouseHealthCheck:
    """`ping()` health check — the ClickHouse-layer equivalent of
    `DatabaseManager.health_check()`. Never raises; a health check that can
    itself fail with an unhandled exception isn't a useful health check.
    """

    def __init__(self, client_manager: ClickHouseClient) -> None:
        self._client_manager = client_manager

    def ping(self, ch_key: str) -> bool:
        try:
            client = self._client_manager.get_client(ch_key)
            return client.ping()
        except (ConfigurationError, DatabaseConnectionError, ClickHouseError) as exc:
            _logger.warning(f"ClickHouse health check failed for '{ch_key}': {exc}")
            return False
