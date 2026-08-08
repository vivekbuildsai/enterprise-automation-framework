from __future__ import annotations

from typing import Any

import pytest
from clickhouse_connect.driver.exceptions import ClickHouseError
from pydantic import HttpUrl

from framework.config.models import ClickHouseConfig, EnvironmentSettings, UiConfig
from framework.database.clickhouse.client import ClickHouseClient
from framework.database.clickhouse.health import ClickHouseHealthCheck
from framework.database.clickhouse.query_executor import ClickHouseQueryExecutor
from framework.database.clickhouse.repository import BaseClickHouseRepository
from framework.database.clickhouse.validator import ClickHouseValidator
from framework.database.exceptions import DatabaseQueryError
from framework.enums.environment import Environment
from framework.exceptions import ConfigurationError
from framework.models import Brand

pytestmark = [pytest.mark.database, pytest.mark.models]


class FakeQueryResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def named_results(self) -> list[dict[str, Any]]:
        return self._rows

    @property
    def result_rows(self) -> list[tuple[Any, ...]]:
        return [tuple(row.values()) for row in self._rows]


class FakeClient:
    """Duck-typed stand-in for `clickhouse_connect.driver.client.Client` —
    only implements the surface this layer actually touches.
    """

    def __init__(self, *, fail_times: int = 0, rows: list[dict[str, Any]] | None = None) -> None:
        self._fail_times = fail_times
        self._calls = 0
        self._rows = rows if rows is not None else []
        self.closed = False
        self.ping_result = True

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> FakeQueryResult:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise ClickHouseError(f"transient failure #{self._calls}")
        return FakeQueryResult(self._rows)

    def ping(self) -> bool:
        return self.ping_result

    def close(self) -> None:
        self.closed = True


def _settings_with_clickhouse(config: ClickHouseConfig) -> EnvironmentSettings:
    return EnvironmentSettings(
        environment=Environment.DEV,
        ui=UiConfig(base_url=HttpUrl("https://example.invalid")),
        clickhouse={"default": config},
    )


class TestClickHouseClient:
    def test_config_for_missing_key_raises_configuration_error(self) -> None:
        manager = ClickHouseClient(_settings_with_clickhouse(ClickHouseConfig()))

        with pytest.raises(ConfigurationError, match="missing"):
            manager.config_for("missing")

    def test_config_for_returns_the_configured_entry(self) -> None:
        config = ClickHouseConfig(enabled=True, host="ch.internal", port=8123)
        manager = ClickHouseClient(_settings_with_clickhouse(config))

        assert manager.config_for("default") is config


class TestClickHouseQueryExecutor:
    def test_query_returns_named_result_dicts(self) -> None:
        client = FakeClient(rows=[{"name": "max_retries", "value": "3"}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        rows = executor.query("SELECT * FROM system_parameters")

        assert rows == [{"name": "max_retries", "value": "3"}]

    def test_query_rows_returns_tuples(self) -> None:
        client = FakeClient(rows=[{"name": "max_retries", "value": "3"}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        rows = executor.query_rows("SELECT * FROM system_parameters")

        assert rows == [("max_retries", "3")]

    def test_query_single_returns_none_for_no_rows(self) -> None:
        client = FakeClient(rows=[])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        assert executor.query_single("SELECT 1") is None

    def test_query_single_raises_for_more_than_one_row(self) -> None:
        client = FakeClient(rows=[{"a": 1}, {"a": 2}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        with pytest.raises(DatabaseQueryError, match="exactly one row"):
            executor.query_single("SELECT * FROM t")

    def test_transient_failure_is_retried_and_succeeds(self) -> None:
        client = FakeClient(fail_times=2, rows=[{"a": 1}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        rows = executor.query("SELECT 1")

        assert rows == [{"a": 1}]
        assert client._calls == 3

    def test_persistent_failure_raises_database_query_error(self) -> None:
        client = FakeClient(fail_times=99, rows=[])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]

        with pytest.raises(DatabaseQueryError):
            executor.query("SELECT 1")


class TestClickHouseHealthCheck:
    def test_ping_true_when_client_reachable(self) -> None:
        client = FakeClient()
        manager = ClickHouseClient(_settings_with_clickhouse(ClickHouseConfig(enabled=True)))
        manager._clients["default"] = client  # type: ignore[assignment]

        assert ClickHouseHealthCheck(manager).ping("default") is True

    def test_ping_false_when_config_missing_never_raises(self) -> None:
        manager = ClickHouseClient(_settings_with_clickhouse(ClickHouseConfig()))

        assert ClickHouseHealthCheck(manager).ping("does-not-exist") is False

    def test_ping_false_when_client_raises(self) -> None:
        class FailingPingClient(FakeClient):
            def ping(self) -> bool:
                raise ClickHouseError("unreachable")

        manager = ClickHouseClient(_settings_with_clickhouse(ClickHouseConfig(enabled=True)))
        manager._clients["default"] = FailingPingClient()  # type: ignore[assignment]

        assert ClickHouseHealthCheck(manager).ping("default") is False


class TestBaseClickHouseRepository:
    def test_require_one_raises_for_missing_row(self) -> None:
        repo: BaseClickHouseRepository[Brand] = BaseClickHouseRepository(
            ClickHouseQueryExecutor(FakeClient())  # type: ignore[arg-type]
        )
        repo.model = Brand

        from framework.database.exceptions import RepositoryError

        with pytest.raises(RepositoryError):
            repo.require_one(None, not_found_message="not found")

    def test_map_one_builds_the_model(self) -> None:
        repo: BaseClickHouseRepository[Brand] = BaseClickHouseRepository(
            ClickHouseQueryExecutor(FakeClient())  # type: ignore[arg-type]
        )
        repo.model = Brand

        brand = repo._map_one({"name": "Acme", "code": "ACM"})

        assert brand == Brand(name="Acme", code="ACM")


class TestClickHouseValidator:
    def test_verify_reports_match(self) -> None:
        result = ClickHouseValidator().verify({"name": "x"}, {"name": "x"})
        assert result.matched is True

    def test_verify_reports_mismatch(self) -> None:
        result = ClickHouseValidator().verify({"name": "x"}, {"name": "y"})
        assert result.matched is False

    def test_verify_handles_none_actual_as_a_mismatch_when_fields_are_explicit(self) -> None:
        # With no `fields=` given, DataComparator only compares keys present
        # in *both* sides — against an empty/None actual, that intersection
        # is empty, so it reports a vacuous match. Passing `fields=`
        # explicitly is how a caller asserts "this field must be present
        # and equal", which is what a real UI -> DB check needs.
        result = ClickHouseValidator().verify({"name": "x"}, None, fields=["name"])
        assert result.matched is False

    def test_verify_without_explicit_fields_is_vacuously_matched_against_none(self) -> None:
        result = ClickHouseValidator().verify({"name": "x"}, None)
        assert result.matched is True
