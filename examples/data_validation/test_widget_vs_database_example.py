"""Example B — UI/Backend Data Validation (the framework's key
differentiator).

Demonstrates the full pipeline:

    UI action (click "Refresh")
          |
    Network / JSON-RPC response  (NetworkInterceptor)
          |
    Widget data extraction        (WidgetDataExtractor + config/dashboards/sample_dashboard.json)
          |
    Database "source of truth"    (DashboardRepository — real class, fake ClickHouse
          |                        client at the transport boundary; no live
          |                        ClickHouse instance is available in this
          |                        sandbox, so this uses the exact same
          |                        RecordingFakeClient pattern the framework's
          |                        own test suite uses — see
          |                        tests/database/clickhouse/unit/test_dashboard_repository.py)
          |
    Normalization                 (aligning both sides on the same field names)
          |
    Tolerance comparison          (DataComparator + Tolerance — real, implemented)
          |
    Validation result             (ComparisonResult.to_report())

Entirely local — no live application or database required.

Run:
    poetry run pytest examples/data_validation -v --alluredir=reports/allure-results
"""

from __future__ import annotations

import json
from typing import Any

import allure
from playwright.sync_api import Page

from framework.database.clickhouse.dashboard_repository import DashboardRepository
from framework.database.clickhouse.query_executor import ClickHouseQueryExecutor
from framework.database.utilities import DataComparator, Tolerance
from framework.models import DashboardConfig
from framework.network import NetworkInterceptor, WidgetDataExtractor


class _FakeClickHouseClient:
    """Stands in for a real `clickhouse_connect` client — same
    duck-typed-fake pattern `tests/database/clickhouse/unit/` already
    uses. Returns deterministic rows instead of talking to a real
    ClickHouse server, which this sandbox doesn't have.
    """

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.last_sql: str | None = None

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> _FakeQueryResult:
        self.last_sql = sql
        return _FakeQueryResult(self._rows)


class _FakeQueryResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def named_results(self) -> list[dict[str, Any]]:
        return self._rows

    @property
    def result_rows(self) -> list[tuple[Any, ...]]:
        return [tuple(row.values()) for row in self._rows]


@allure.feature("Example: UI + Backend Data Validation")
@allure.story("A dashboard widget's UI value matches the database within tolerance")
def test_widget_data_matches_database_within_tolerance(page: Page) -> None:
    dashboard_config = DashboardConfig.load("sample_dashboard")
    widget_id = "top-countries-by-usage"
    widget = dashboard_config.widget(widget_id)

    with allure.step("Serve a local page with a mocked dashboard API response"):
        page.set_content('<html><body><button id="refresh">Refresh</button></body></html>')
        # The UI shows 1005 for the US — 5 more than the database's 1000,
        # a realistic small drift (e.g. a slightly later snapshot).
        ui_response = {"rows": [{"country": "US", "usage_units": 1005}]}
        page.route(
            "https://example.test/api/dashboard",
            lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(ui_response)
            ),
        )

    # The request body carries the widget request identifier
    # ("widget=top-countries") — this is what `widget.identify.must_have`
    # actually matches against (see config/dashboards/sample_dashboard.json),
    # the same way a real dashboard's JSON-RPC/XHR request body would.
    with (
        allure.step("Click 'Refresh' and capture the real network exchange"),
        NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor,
    ):
        page.evaluate(
            """() => fetch('https://example.test/api/dashboard', {
                method: 'POST',
                body: 'widget=top-countries',
            })"""
        )
        page.wait_for_timeout(50)

    with allure.step("Extract widget data from the captured response"):
        exchange = WidgetDataExtractor.find_matching(widget.identify, interceptor.captured)
        assert (
            exchange is not None
        ), "the mocked dashboard response should match the widget's identify rule"
        ui_rows = WidgetDataExtractor.extract_rows(exchange, widget.extractors)
        ui_us_row = next(row for row in ui_rows if row["dimension"] == "US")

    with allure.step("Reproduce the same number from the database (ClickHouse — faked transport)"):
        fake_client = _FakeClickHouseClient(rows=[{"dimension": "US", "total": 1000}])
        executor = ClickHouseQueryExecutor(fake_client)  # type: ignore[arg-type]
        repository = DashboardRepository(executor, database="example_db")
        db_rows = repository.run_widget_query(
            dashboard_config, widget_id, date_from_unix=1_700_000_000, date_to_unix=1_710_000_000
        )
        db_us_row = next(row for row in db_rows if row["dimension"] == "US")

    with allure.step("Normalize both sides onto the same field names"):
        expected = {"dimension": db_us_row["dimension"], "total": db_us_row["total"]}
        actual = {"dimension": ui_us_row["dimension"], "total": ui_us_row["usage_units"]}

    with allure.step(
        f"Compare within the widget's configured tolerance (±{widget.tolerance_pct}%)"
    ):
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Database",
            right_label="UI Widget",
            tolerance=Tolerance(percentage=widget.tolerance_pct),
        )
        allure.attach(
            result.to_report(),
            name="Validation result",
            attachment_type=allure.attachment_type.TEXT,
        )

        assert result.matched, result.to_report()
        total_comparison = next(fc for fc in result.field_comparisons if fc.field == "total")
        assert total_comparison.difference_pct == 0.5
