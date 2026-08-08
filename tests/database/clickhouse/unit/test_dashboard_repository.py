from __future__ import annotations

from typing import Any

import pytest

from framework.database.clickhouse.dashboard_repository import DashboardRepository
from framework.database.clickhouse.query_executor import ClickHouseQueryExecutor
from framework.exceptions import ConfigurationError
from framework.models import DashboardConfig

pytestmark = pytest.mark.database


class FakeQueryResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def named_results(self) -> list[dict[str, Any]]:
        return self._rows

    @property
    def result_rows(self) -> list[tuple[Any, ...]]:
        return [tuple(row.values()) for row in self._rows]


class RecordingFakeClient:
    """Records the exact SQL text it was asked to run, so tests can assert
    on the real template-filling output — not just that a query executed.
    """

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self._rows = rows if rows is not None else []
        self.last_sql: str | None = None

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> FakeQueryResult:
        self.last_sql = sql
        return FakeQueryResult(self._rows)


@pytest.fixture
def dashboard_config() -> DashboardConfig:
    return DashboardConfig.load("sample_dashboard")


class TestDashboardConfigLoading:
    def test_loads_the_sample_config(self, dashboard_config: DashboardConfig) -> None:
        assert dashboard_config.dashboard_id == "sample-dashboard"
        assert len(dashboard_config.widgets) == 1
        assert len(dashboard_config.export_validation) == 1
        assert dashboard_config.host.default_id == 1

    def test_widget_raises_for_unknown_id(self, dashboard_config: DashboardConfig) -> None:
        with pytest.raises(ConfigurationError, match="no widget"):
            dashboard_config.widget("does-not-exist")

    def test_export_raises_for_unknown_key(self, dashboard_config: DashboardConfig) -> None:
        with pytest.raises(ConfigurationError, match="no export validation"):
            dashboard_config.export("does-not-exist")


class TestDashboardRepositoryTemplateFilling:
    def test_run_widget_query_fills_all_placeholders(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient(rows=[{"dimension": "US", "total": 100}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]
        repo = DashboardRepository(executor, database="sample_ch")

        rows = repo.run_widget_query(
            dashboard_config,
            "top-countries-by-usage",
            date_from_unix=1700000000,
            date_to_unix=1710000000,
        )

        assert rows == [{"dimension": "US", "total": 100}]
        assert client.last_sql is not None
        assert "{{" not in client.last_sql
        assert "sample_ch.daily_usage_summary" in client.last_sql
        assert "host_id IN (1)" in client.last_sql  # config's default host id
        assert "1700000000" in client.last_sql
        assert "1710000000" in client.last_sql

    def test_run_widget_query_honors_an_explicit_host_id(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient()
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]
        repo = DashboardRepository(executor, database="sample_ch")

        repo.run_widget_query(
            dashboard_config,
            "top-countries-by-usage",
            host_id=999,
            date_from_unix=1,
            date_to_unix=2,
        )

        assert client.last_sql is not None
        assert "host_id IN (999)" in client.last_sql

    def test_run_widget_query_raises_for_unknown_widget(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient()
        repo = DashboardRepository(
            ClickHouseQueryExecutor(client), database="sample_ch"  # type: ignore[arg-type]
        )

        with pytest.raises(ConfigurationError):
            repo.run_widget_query(
                dashboard_config, "does-not-exist", date_from_unix=1, date_to_unix=2
            )

    def test_run_export_total_parses_the_single_value(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient(rows=[{"total": 12345}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]
        repo = DashboardRepository(executor, database="sample_ch")

        total = repo.run_export_total(
            dashboard_config, "totalUsage", date_from_unix=1, date_to_unix=2
        )

        assert total == 12345.0
        assert client.last_sql is not None
        assert "daily_usage_summary" in client.last_sql

    def test_run_export_total_defaults_to_zero_for_no_rows(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient(rows=[])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]
        repo = DashboardRepository(executor, database="sample_ch")

        total = repo.run_export_total(
            dashboard_config, "totalUsage", date_from_unix=1, date_to_unix=2
        )

        assert total == 0.0

    def test_run_export_per_row_uses_the_per_row_template(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient(rows=[{"country": "US", "total": 42}])
        executor = ClickHouseQueryExecutor(client)  # type: ignore[arg-type]
        repo = DashboardRepository(executor, database="sample_ch")

        rows = repo.run_export_per_row(
            dashboard_config, "totalUsage", date_from_unix=1, date_to_unix=2
        )

        assert rows == [{"country": "US", "total": 42}]
        assert client.last_sql is not None
        assert "GROUP BY country" in client.last_sql

    def test_run_export_per_row_raises_for_unknown_export(
        self, dashboard_config: DashboardConfig
    ) -> None:
        client = RecordingFakeClient()
        repo = DashboardRepository(
            ClickHouseQueryExecutor(client), database="sample_ch"  # type: ignore[arg-type]
        )

        with pytest.raises(ConfigurationError):
            repo.run_export_per_row(
                dashboard_config, "does-not-exist", date_from_unix=1, date_to_unix=2
            )
