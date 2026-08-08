from __future__ import annotations

from typing import Any

from framework.database.clickhouse.validator import ClickHouseValidator
from framework.database.utilities.comparison import ComparisonResult


class ValidationService:
    """Top-level "verify what the UI showed against what the database
    actually has" entry point, so a test calls one method regardless of
    which underlying validator does the comparison — `ClickHouseValidator`
    here, the existing SQLAlchemy-backed
    `framework.database.validators.*` classes for other domains. This is
    what makes "UI -> Database -> Report without changing tests" possible:
    the comparison backend is a constructor detail, not something the
    calling test ever sees.
    """

    def __init__(self, clickhouse_validator: ClickHouseValidator) -> None:
        self._clickhouse_validator = clickhouse_validator

    def verify_ui_against_database(
        self,
        ui_values: dict[str, Any],
        expected: dict[str, Any],
        *,
        fields: list[str] | None = None,
        name: str = "UI vs Database",
    ) -> ComparisonResult:
        return self._clickhouse_validator.verify(expected, ui_values, fields=fields, name=name)
