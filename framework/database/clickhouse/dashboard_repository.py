from __future__ import annotations

from typing import Any

from framework.database.clickhouse.query_executor import ClickHouseQueryExecutor
from framework.models import DashboardConfig


class DashboardRepository:
    """Runs the SQL templates declared in a `DashboardConfig`
    (`config/dashboards/*.json`) against ClickHouse via
    `ClickHouseQueryExecutor` — the database half of the
    UI-widget-vs-database-source-of-truth validation pipeline: a page
    captures/extracts what a dashboard widget displayed, this repository
    reproduces the same number from the database, and a validator (see
    `framework.database.utilities.comparison`) compares the two within a
    configured tolerance.

    Unlike `BaseClickHouseRepository`'s single-model repositories, results
    here are ad-hoc dimension/metric rows (or a single float for an
    export's total), since dashboard queries don't map onto one fixed
    dataclass.
    """

    def __init__(self, executor: ClickHouseQueryExecutor, *, database: str) -> None:
        self._executor = executor
        self._database = database

    def _fill_template(
        self, template: str, *, host_id: int, date_from_unix: int, date_to_unix: int
    ) -> str:
        return (
            template.replace("{{CH_DATABASE}}", self._database)
            .replace("{{HOST_ID}}", str(host_id))
            .replace("{{DATE_FROM_UNIX}}", str(date_from_unix))
            .replace("{{DATE_TO_UNIX}}", str(date_to_unix))
        )

    def run_widget_query(
        self,
        config: DashboardConfig,
        widget_id: str,
        *,
        host_id: int | None = None,
        date_from_unix: int,
        date_to_unix: int,
    ) -> list[dict[str, Any]]:
        widget = config.widget(widget_id)
        sql = self._fill_template(
            widget.ch_query_template,
            host_id=host_id if host_id is not None else config.host.default_id,
            date_from_unix=date_from_unix,
            date_to_unix=date_to_unix,
        )
        return self._executor.query(sql)

    def run_export_total(
        self,
        config: DashboardConfig,
        export_key: str,
        *,
        host_id: int | None = None,
        date_from_unix: int,
        date_to_unix: int,
    ) -> float:
        export = config.export(export_key)
        sql = self._fill_template(
            export.total_template,
            host_id=host_id if host_id is not None else config.host.default_id,
            date_from_unix=date_from_unix,
            date_to_unix=date_to_unix,
        )
        row = self._executor.query_single(sql)
        if row is None:
            return 0.0
        return float(next(iter(row.values())))

    def run_export_per_row(
        self,
        config: DashboardConfig,
        export_key: str,
        *,
        host_id: int | None = None,
        date_from_unix: int,
        date_to_unix: int,
    ) -> list[dict[str, Any]]:
        export = config.export(export_key)
        sql = self._fill_template(
            export.per_row_template,
            host_id=host_id if host_id is not None else config.host.default_id,
            date_from_unix=date_from_unix,
            date_to_unix=date_to_unix,
        )
        return self._executor.query(sql)
