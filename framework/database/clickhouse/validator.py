from __future__ import annotations

from typing import Any

from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class ClickHouseValidator:
    """Generic UI/business-value <-> ClickHouse comparison — reuses the
    same `DataComparator`/`ComparisonResult` the SQLAlchemy-backed
    `framework.database.validators.*` classes already use (nothing about
    that comparison logic is SQLAlchemy-specific), so `UI -> Database ->
    Report` works without a test ever touching Playwright/ClickHouse
    directly. Kept domain-agnostic here rather than one validator per
    business entity (SubscriberValidator, SystemParameterValidator, ...),
    since no real ClickHouse query exists yet for any of them to compare
    against — callers pass in whatever `actual` dict a (currently stub)
    repository would eventually fetch.
    """

    def verify(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any] | None,
        *,
        fields: list[str] | None = None,
        name: str = "ClickHouse Validation",
    ) -> ComparisonResult:
        result = DataComparator.compare(
            expected,
            actual or {},
            left_label="Expected",
            right_label="ClickHouse",
            fields=fields,
        )
        attach_comparison_result(result, name=name)
        return result
