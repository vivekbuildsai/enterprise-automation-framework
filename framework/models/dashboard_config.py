from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from framework.exceptions import ConfigurationError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DASHBOARDS_DIR = _PROJECT_ROOT / "config" / "dashboards"


class DateRangeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str = ""
    date_from_ui: str = Field(alias="dateFromUi")
    date_to_ui: str = Field(alias="dateToUi")
    date_from_db: str = Field(alias="dateFromDb")
    date_to_db: str = Field(alias="dateToDb")


class GranularityOption(BaseModel):
    label: str
    table: str


class GranularityConfig(BaseModel):
    active: str
    options: dict[str, GranularityOption]


class HostConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    default_id: int = Field(alias="defaultId")
    default_label: str = Field(alias="defaultLabel")


class TimeoutsConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ui_before_all_ms: int = Field(alias="uiBeforeAllMs")


class ExportValidationConfig(BaseModel):
    """One entry of `exportValidation` — a metric export (e.g. a CSV/report
    download) the target application's UI can be asked to produce, with
    the matching ClickHouse query templates to validate it against.
    """

    model_config = ConfigDict(populate_by_name=True)

    description: str = ""
    tolerance_pct: float = Field(alias="tolerancePct", default=2.0)
    total_template: str = Field(alias="totalTemplate")
    per_row_template: str = Field(alias="perRowTemplate")


class WidgetIdentify(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    must_have: list[str] = Field(alias="mustHave", default_factory=list)
    must_not_have: list[str] = Field(alias="mustNotHave", default_factory=list)
    skip_if_request_contains: str | None = Field(alias="skipIfRequestContains", default=None)
    require_if_request_contains: str | None = Field(alias="requireIfRequestContains", default=None)


class WidgetExtractors(BaseModel):
    dimension: str
    metric: str | list[str]


class WidgetConfig(BaseModel):
    """One dashboard widget (e.g. a "Top Countries" chart or KPI tile) —
    how to spot it in a captured UI/network request (`identify`) and the
    ClickHouse query that should reproduce what it displays.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    tab: str
    sub_tab: str | None = Field(alias="subTab", default=None)
    identify: WidgetIdentify
    extractors: WidgetExtractors
    ch_query_template: str = Field(alias="chQueryTemplate")
    top_n: int = Field(alias="topN", default=10)
    tolerance_pct: float = Field(alias="tolerancePct", default=2.0)
    min_volume_for_assertion: int = Field(alias="minVolumeForAssertion", default=0)
    multi_response: bool = Field(alias="multiResponse", default=False)


class DashboardConfig(BaseModel):
    """A dashboard's full validation config, loaded from
    `config/dashboards/{dashboard_id}.json`: which widgets exist, how to
    identify each one in a captured UI/network request, and the
    ClickHouse query template that should reproduce what it displays —
    the configuration-driven half of the widget-vs-database validation
    pipeline (see `framework.database.clickhouse.DashboardRepository`).
    """

    model_config = ConfigDict(populate_by_name=True)

    dashboard_id: str = Field(alias="dashboardId")
    name: str
    date_range: DateRangeConfig = Field(alias="dateRange")
    granularity: GranularityConfig
    host: HostConfig
    segment_type: str = Field(alias="segmentType")
    filter_comparison_widget_id: str = Field(alias="filterComparisonWidgetId")
    mandatory_filters: list[str] = Field(alias="mandatoryFilters", default_factory=list)
    tolerance_pct: float = Field(alias="tolerancePct", default=2.0)
    timeouts: TimeoutsConfig
    export_validation: dict[str, ExportValidationConfig] = Field(alias="exportValidation")
    widgets: list[WidgetConfig]

    @classmethod
    def load(cls, dashboard_id: str) -> DashboardConfig:
        """Loads `config/dashboards/{dashboard_id}.json` — the same
        "real file on disk, not a Python literal" convention
        `config/environments/*.yaml` already uses for environment config.
        """
        config_path = _DASHBOARDS_DIR / f"{dashboard_id}.json"
        if not config_path.exists():
            raise ConfigurationError(
                f"No dashboard config found for '{dashboard_id}' at {config_path}"
            )
        with config_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return cls.model_validate(raw)

    def widget(self, widget_id: str) -> WidgetConfig:
        for widget in self.widgets:
            if widget.id == widget_id:
                return widget
        raise ConfigurationError(
            f"Dashboard '{self.dashboard_id}' has no widget '{widget_id}' — "
            f"available: {', '.join(w.id for w in self.widgets)}"
        )

    def export(self, export_key: str) -> ExportValidationConfig:
        try:
            return self.export_validation[export_key]
        except KeyError as exc:
            available = ", ".join(self.export_validation)
            raise ConfigurationError(
                f"Dashboard '{self.dashboard_id}' has no export validation "
                f"'{export_key}' — available: {available}"
            ) from exc
