from __future__ import annotations

from dataclasses import asdict
from typing import Any

from framework.database.repositories import AuditRepository
from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


class AuditValidator:
    """Cross-layer validation for the Audit Log domain (see
    `SubscriberValidator` for the shared design rationale). Most useful for
    confirming that a UI/API action (e.g. "Modified by: Admin") actually
    produced a corresponding audit trail row, rather than field-by-field
    record comparison.
    """

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def verify_against_database(
        self, audit_id: str, expected: dict[str, Any], *, fields: list[str] | None = None
    ) -> ComparisonResult:
        actual = asdict(self._repository.get_by_id(audit_id))
        result = DataComparator.compare(
            expected,
            actual,
            left_label="Expected Audit Entry",
            right_label="Database Audit Entry",
            fields=fields,
        )
        attach_comparison_result(result, name="Audit Entry Database Validation")
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
            left_label="Expected Audit Entry",
            right_label="API Audit Entry",
            fields=fields,
        )
        attach_comparison_result(result, name="Audit Entry API Validation")
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
            left_label="Expected Audit Entry",
            right_label="UI Audit Entry",
            fields=fields,
        )
        attach_comparison_result(result, name="Audit Entry UI Validation")
        return result

    def verify_entity_was_audited(
        self, entity_type: str, entity_id: str, *, expected_action: str
    ) -> bool:
        """Confirms *some* audit row exists for `entity_type`/`entity_id`
        with `expected_action` — the common case (did this action get
        logged at all) that doesn't need a full field-by-field comparison.
        """
        entries = self._repository.find_by_entity(entity_type, entity_id)
        return any(entry.action == expected_action for entry in entries)

    def verify_all(
        self,
        audit_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = [self.verify_against_database(audit_id, expected, fields=fields)]
        if api_payload is not None:
            results.append(self.verify_against_api(api_payload, expected, fields=fields))
        if ui_values is not None:
            results.append(self.verify_against_ui(ui_values, expected, fields=fields))
        return results

    def verify_all_or_raise(
        self,
        audit_id: str,
        *,
        expected: dict[str, Any],
        api_payload: dict[str, Any] | None = None,
        ui_values: dict[str, Any] | None = None,
        fields: list[str] | None = None,
    ) -> list[ComparisonResult]:
        results = self.verify_all(
            audit_id, expected=expected, api_payload=api_payload, ui_values=ui_values, fields=fields
        )
        for result in results:
            result.raise_if_mismatched()
        return results
