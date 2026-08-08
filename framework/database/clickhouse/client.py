from __future__ import annotations

from clickhouse_connect.driver.client import Client

from framework.config.models import ClickHouseConfig, EnvironmentSettings
from framework.database.clickhouse.connection import ClickHouseConnectionFactory
from framework.exceptions import ConfigurationError
from framework.logger import get_logger

_logger = get_logger("ClickHouseClient")


class ClickHouseClient:
    """Top-level entry point to the ClickHouse layer. Owns one
    `clickhouse_connect` `Client` per `ch_key` (a name in
    `settings.clickhouse`, e.g. `"default"`), created lazily on first use and
    cached — the ClickHouse-layer equivalent of
    `framework.database.connection.DatabaseManager`.
    """

    def __init__(self, settings: EnvironmentSettings) -> None:
        self._settings = settings
        self._clients: dict[str, Client] = {}

    def config_for(self, ch_key: str) -> ClickHouseConfig:
        try:
            return self._settings.clickhouse[ch_key]
        except KeyError as exc:
            env_name = self._settings.environment.value
            raise ConfigurationError(
                f"No ClickHouse config for '{ch_key}' in the '{env_name}' environment — "
                f"add it under `clickhouse:` in config/environments/{env_name}.yaml"
            ) from exc

    def get_client(self, ch_key: str) -> Client:
        """Lazily creates (on first call) and caches the `Client` for
        `ch_key`. Safe to call repeatedly — subsequent calls are a dict
        lookup, not a new connection.
        """
        if ch_key not in self._clients:
            config = self.config_for(ch_key)
            self._clients[ch_key] = ClickHouseConnectionFactory.create_client(config)
        return self._clients[ch_key]

    def close(self, ch_key: str) -> None:
        client = self._clients.pop(ch_key, None)
        if client is not None:
            client.close()  # type: ignore[no-untyped-call]

    def close_all(self) -> None:
        for ch_key in list(self._clients):
            self.close(ch_key)
