from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import AlarmRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class AlarmValidator:
    """Cross-layer validation for the Alarm domain (see
    `SubscriberValidator` for the shared design rationale).
    """

    def __init__(self, repository: AlarmRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, alarm_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(alarm_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Alarm",
            right_label="Database Alarm",
            fields=fields,
        )
        attach_comparison_result(result, name="Alarm Database Validation")
        return result

    def verify_against_api(
        self,
        api_payload: dict[str, Any],
        expected: dict[str, Any],
        *,
        fields: list[str] | None = None,
    ) -> ComparisonResult:
        result = DataComparator.compare(
            expected,
            api_payload,
            left_label="Expected Alarm",
            right_label="API Alarm",
            fields=fields,
        )
        attach_comparison_result(result, name="Alarm API Validation")
        return result

    def verify_against_ui(
        self,
        ui_values: dict[str, Any],
        expected: dict[str, Any],
        *,
        fields: list[str] | None = None,
    ) -> ComparisonResult:
        result = DataComparator.compare(
            expected, ui_values, left_label="Expected Alarm", right_label="UI Alarm", fields=fields
        )
        attach_comparison_result(result, name="Alarm UI Validation")
        return result

    def verify_all(
        self,
        alarm_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(alarm_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        alarm_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            alarm_id, expected=expected, api_payload=api_payload, ui_values=ui_values, fields=fields
        )
        for result in results:
            result.raise_if_mismatched()
        return results
