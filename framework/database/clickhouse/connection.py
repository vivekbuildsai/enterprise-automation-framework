from __future__ import annotations

from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError

from framework.config.models import ClickHouseConfig
from framework.database.exceptions import DatabaseConnectionError


class ClickHouseConnectionFactory:
    """Turns a `ClickHouseConfig` into a live `clickhouse_connect` `Client`
    — the ClickHouse-layer equivalent of
    `framework.database.connection.ConnectionFactory`, kept separate since
    ClickHouse isn't one of that factory's supported SQLAlchemy dialects.
    """

    @staticmethod
    def create_client(config: ClickHouseConfig) -> Client:
        try:
            return get_client(
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password,
                database=config.database or "__default__",
                interface=config.protocol,
            )
        except ClickHouseError as exc:
            raise DatabaseConnectionError(
                f"Failed to connect to ClickHouse at {config.host}:{config.port}: {exc}"
            ) from exc
