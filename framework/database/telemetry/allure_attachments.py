from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import allure

from framework.database.utilities.result_mapper import ExecutionResult
from framework.logger import get_logger

if TYPE_CHECKING:
    from framework.database.utilities.comparison import ComparisonResult

_logger = get_logger("DatabaseTelemetry")

_MAX_ROWS_ATTACHED = 50


def attach_query_telemetry(result: ExecutionResult, *, environment: str = "") -> None:
    """Attaches one executed statement to the Allure report: the SQL text,
    a JSON telemetry summary (execution time, row count, database name,
    environment), and (capped) the returned rows. Best-effort, matching the
    API layer's `allure_middleware` — a missing/inactive Allure context must
    never fail the actual test.
    """
    try:
        summary: dict[str, Any] = {
            "database": result.database,
            "dialect": result.dialect,
            "environment": environment,
            "execution_time_ms": round(result.elapsed_ms, 2),
            "returned_rows": result.rowcount,
            "succeeded": result.succeeded,
        }
        if result.error:
            summary["error"] = result.error

        allure.attach(
            result.sql,
            name=f"SQL: {result.database}",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            json.dumps(summary, indent=2, default=str),
            name="Query Telemetry",
            attachment_type=allure.attachment_type.JSON,
        )
        if result.rows:
            allure.attach(
                json.dumps(result.rows[:_MAX_ROWS_ATTACHED], indent=2, default=str),
                name=f"Returned Rows (first {min(len(result.rows), _MAX_ROWS_ATTACHED)})",
                attachment_type=allure.attachment_type.JSON,
            )
    except Exception:  # noqa: BLE001 - reporting must never break the test
        _logger.debug("Skipped Allure query telemetry attachment (no active test context)")


def attach_comparison_result(
    comparison: ComparisonResult, *, name: str = "Validation Summary"
) -> None:
    """Attaches a `DataComparator` result (UI/API/DB cross-check) to Allure
    as a human-readable diff, so a failing hybrid assertion is diagnosable
    straight from the report instead of requiring a local re-run.
    """
    try:
        allure.attach(
            comparison.to_report(),
            name=name,
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:  # noqa: BLE001 - reporting must never break the test
        _logger.debug("Skipped Allure comparison attachment (no active test context)")


def attach_layer_result(layer: str, value: Any, *, name: str | None = None) -> None:
    """Generic hook for attaching a single layer's raw result (e.g. the API
    response body, or the UI's displayed value) alongside the DB/comparison
    attachments — used by `ValidationFacade` so the report shows exactly
    what each layer returned, not just whether they matched.
    """
    try:
        payload = value if isinstance(value, str) else json.dumps(value, indent=2, default=str)
        allure.attach(
            payload,
            name=name or f"{layer.upper()} Result",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:  # noqa: BLE001 - reporting must never break the test
        _logger.debug(f"Skipped Allure {layer} result attachment (no active test context)")
