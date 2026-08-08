from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from framework.database.telemetry import attach_comparison_result
from framework.database.utilities.comparison import ComparisonResult, DataComparator


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"Expected a dict or dataclass instance, got {type(value).__name__}")


class DatabaseValidator:
    """Generic, domain-agnostic DB-only comparison: "does this actual row
    (dict or dataclass) match this expected dict of field values". The
    six domain validators (`SubscriberValidator`, etc.) build on this for
    their DB leg and add the API/UI legs — this class exists so that
    generic logic isn't duplicated six times.
    """

    @staticmethod
    def verify_matches(
        actual: Any,
        expected: dict[str, Any],
        *,
        entity_label: str,
        fields: list[str] | None = None,
        attach_report: bool = True,
    ) -> ComparisonResult:
        result = DataComparator.compare(
            expected,
            _as_dict(actual),
            left_label=f"Expected {entity_label}",
            right_label=f"Database {entity_label}",
            fields=fields,
        )
        if attach_report:
            attach_comparison_result(result, name=f"{entity_label} Database Validation")
        return result

    @staticmethod
    def verify_matches_or_raise(
        actual: Any, expected: dict[str, Any], *, entity_label: str, fields: list[str] | None = None
    ) -> ComparisonResult:
        result = DatabaseValidator.verify_matches(
            actual, expected, entity_label=entity_label, fields=fields
        )
        result.raise_if_mismatched()
        return result
