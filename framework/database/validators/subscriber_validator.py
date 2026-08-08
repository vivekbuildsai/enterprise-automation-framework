from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import SubscriberRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class SubscriberValidator:
    """Cross-layer validation for the Subscriber domain: compares one
    expected record against what the database, API, and/or UI actually
    show. Every `verify_*` method returns a `ComparisonResult` rather than
    raising by default, so a hybrid test can inspect every layer's outcome
    before deciding what to assert on — use the `_or_raise` variant (or call
    `.raise_if_mismatched()` on the result) when any mismatch should fail
    the test immediately.
    """

    def __init__(self, repository: SubscriberRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, subscriber_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(subscriber_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Subscriber",
            right_label="Database Subscriber",
            fields=fields,
        )
        attach_comparison_result(result, name="Subscriber Database Validation")
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
            left_label="Expected Subscriber",
            right_label="API Subscriber",
            fields=fields,
        )
        attach_comparison_result(result, name="Subscriber API Validation")
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
            left_label="Expected Subscriber",
            right_label="UI Subscriber",
            fields=fields,
        )
        attach_comparison_result(result, name="Subscriber UI Validation")
        return result

    def verify_all(
        self,
        subscriber_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(subscriber_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        subscriber_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            subscriber_id,
            expected=expected,
            api_payload=api_payload,
            ui_values=ui_values,
            fields=fields,
        )
        for result in results:
            result.raise_if_mismatched()
        return results
