from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import NetworkRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class NetworkValidator:
    """Cross-layer validation for the Network domain (see
    `SubscriberValidator` for the shared design rationale).
    """

    def __init__(self, repository: NetworkRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, network_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(network_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Network",
            right_label="Database Network",
            fields=fields,
        )
        attach_comparison_result(result, name="Network Database Validation")
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
            left_label="Expected Network",
            right_label="API Network",
            fields=fields,
        )
        attach_comparison_result(result, name="Network API Validation")
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
            left_label="Expected Network",
            right_label="UI Network",
            fields=fields,
        )
        attach_comparison_result(result, name="Network UI Validation")
        return result

    def verify_all(
        self,
        network_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(network_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        network_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            network_id,
            expected=expected,
            api_payload=api_payload,
            ui_values=ui_values,
            fields=fields,
        )
        for result in results:
            result.raise_if_mismatched()
        return results
