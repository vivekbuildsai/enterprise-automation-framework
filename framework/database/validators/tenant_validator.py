from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import TenantRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class TenantValidator:
    """Cross-layer validation for the Tenant domain (see `SubscriberValidator`
    for the shared design rationale).
    """

    def __init__(self, repository: TenantRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, tenant_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(tenant_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Tenant",
            right_label="Database Tenant",
            fields=fields,
        )
        attach_comparison_result(result, name="Tenant Database Validation")
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
            left_label="Expected Tenant",
            right_label="API Tenant",
            fields=fields,
        )
        attach_comparison_result(result, name="Tenant API Validation")
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
            left_label="Expected Tenant",
            right_label="UI Tenant",
            fields=fields,
        )
        attach_comparison_result(result, name="Tenant UI Validation")
        return result

    def verify_all(
        self,
        tenant_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(tenant_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        tenant_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            tenant_id,
            expected=expected,
            api_payload=api_payload,
            ui_values=ui_values,
            fields=fields,
        )
        for result in results:
            result.raise_if_mismatched()
        return results
