from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import SteeringRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class SteeringValidator:
    """Cross-layer validation for the Steering of Roaming domain — the
    validation counterpart to the real Steering Overview screen (see
    `SubscriberValidator` for the shared design rationale).
    """

    def __init__(self, repository: SteeringRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, zone_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(zone_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Steering Zone",
            right_label="Database Steering Zone",
            fields=fields,
        )
        attach_comparison_result(result, name="Steering Zone Database Validation")
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
            left_label="Expected Steering Zone",
            right_label="API Steering Zone",
            fields=fields,
        )
        attach_comparison_result(result, name="Steering Zone API Validation")
        return result

    def verify_against_ui(
        self,
        ui_values: dict[str, Any],
        expected: dict[str, Any],
        *,
        fields: list[str] | None = None,
    ) -> ComparisonResult:
        result = DataComparator.compare(
            expected,
            ui_values,
            left_label="Expected Steering Zone",
            right_label="UI Steering Zone",
            fields=fields,
        )
        attach_comparison_result(result, name="Steering Zone UI Validation")
        return result

    def verify_all(
        self,
        zone_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(zone_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        zone_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            zone_id, expected=expected, api_payload=api_payload, ui_values=ui_values, fields=fields
        )
        for result in results:
            result.raise_if_mismatched()
        return results
