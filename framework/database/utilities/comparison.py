from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from framework.database.exceptions import DataComparisonError


@dataclass(frozen=True, slots=True)
class Tolerance:
    """Percentage and/or absolute tolerance for numeric field comparison.

    At least one of `percentage`/`absolute` must be set. When both are
    set, a field passes if it satisfies *either* one — the more
    permissive check. This matters most for a near-zero expected value,
    where a percentage tolerance alone is either meaningless (expected
    exactly `0`) or too strict (expected `0.01`); pairing it with a small
    absolute tolerance covers that case without weakening the percentage
    check for everything else.

    `percentage` is a plain number, not a fraction — `Tolerance(percentage=1.0)`
    means "within ±1%", not "within ±100%".
    """

    percentage: float | None = None
    absolute: float | None = None

    def __post_init__(self) -> None:
        if self.percentage is None and self.absolute is None:
            raise ValueError("Tolerance requires at least one of percentage=/absolute=")


@dataclass(frozen=True, slots=True)
class FieldDiff:
    field: str
    left_value: Any
    right_value: Any

    def __str__(self) -> str:
        return f"{self.field}: {self.left_value!r} != {self.right_value!r}"


@dataclass(frozen=True, slots=True)
class FieldComparison:
    """Full detail for one compared field — populated for every field
    `compare()` checks, whether it matched or not, so a caller (or a
    report) can see exactly how each field was evaluated, not just which
    ones failed. This is the structured result the numeric tolerance
    engine exposes; `ComparisonResult.diffs`/`.to_report()` stay exactly
    as before for callers that only care about mismatches.
    """

    field: str
    expected: Any
    actual: Any
    # "exact" | "percentage_tolerance" | "absolute_tolerance" | "percentage_or_absolute_tolerance"
    comparison_type: str
    matched: bool
    tolerance: Tolerance | None = None
    difference: float | None = None  # abs(actual - expected), numeric comparisons only
    difference_pct: float | None = None  # None when expected == 0 (percentage is undefined)
    message: str = ""

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """The output of one `DataComparator` comparison — human-readable by
    design (`to_report()`) so a hybrid-validation failure is diagnosable
    straight from the Allure attachment or pytest failure message, without
    re-running the test to see what actually differed.
    """

    left_label: str
    right_label: str
    matched: bool
    diffs: list[FieldDiff] = field(default_factory=list)
    compared_fields: list[str] = field(default_factory=list)
    field_comparisons: list[FieldComparison] = field(default_factory=list)

    def to_report(self) -> str:
        if self.matched:
            fields = ", ".join(self.compared_fields)
            return f"{self.left_label} == {self.right_label}: MATCH on [{fields}]"
        lines = [f"{self.left_label} vs {self.right_label}: MISMATCH"]
        if self.field_comparisons:
            lines.extend(f"  - {fc.message}" for fc in self.field_comparisons if not fc.matched)
        else:
            lines.extend(f"  - {diff}" for diff in self.diffs)
        return "\n".join(lines)

    def raise_if_mismatched(self) -> None:
        if not self.matched:
            raise DataComparisonError(self.to_report())


_Number = (int, float)


class DataComparator:
    """Reusable field-by-field comparison across UI/API/DB dict-like
    payloads. `ValidationFacade` and the business validators build on this
    rather than each hand-rolling their own equality checks — one place
    that decides what "matches" means (case/whitespace-insensitive string
    comparison, optionally numeric tolerance) and how a mismatch is
    reported.
    """

    @staticmethod
    def compare(
        left: dict[str, Any],
        right: dict[str, Any],
        *,
        left_label: str,
        right_label: str,
        fields: list[str] | None = None,
        tolerance: Tolerance | None = None,
    ) -> ComparisonResult:
        """`left` is the expected/reference side for tolerance's
        percentage-difference math (matches this codebase's existing
        convention of calling `compare(expected, actual, ...)`).
        `tolerance` applies to every compared field that holds a numeric
        value on both sides; non-numeric fields (and fields where either
        side is `None`) always use exact/normalized comparison regardless
        of `tolerance`.
        """
        compared_fields = fields if fields is not None else sorted(set(left) & set(right))
        field_comparisons = [
            DataComparator._compare_field(f, left.get(f), right.get(f), tolerance)
            for f in compared_fields
        ]
        diffs = [
            FieldDiff(field=fc.field, left_value=fc.expected, right_value=fc.actual)
            for fc in field_comparisons
            if not fc.matched
        ]
        return ComparisonResult(
            left_label=left_label,
            right_label=right_label,
            matched=not diffs,
            diffs=diffs,
            compared_fields=compared_fields,
            field_comparisons=field_comparisons,
        )

    @staticmethod
    def _compare_field(
        field_name: str, expected: Any, actual: Any, tolerance: Tolerance | None
    ) -> FieldComparison:
        if expected is None or actual is None:
            matched = expected is None and actual is None
            message = (
                f"{field_name}: match (both null)"
                if matched
                else f"{field_name}: {expected!r} != {actual!r}"
            )
            return FieldComparison(
                field=field_name,
                expected=expected,
                actual=actual,
                comparison_type="exact",
                matched=matched,
                message=message,
            )

        is_numeric_pair = (
            isinstance(expected, _Number)
            and not isinstance(expected, bool)
            and isinstance(actual, _Number)
            and not isinstance(actual, bool)
        )

        if tolerance is not None and is_numeric_pair:
            return DataComparator._compare_numeric_with_tolerance(
                field_name, expected, actual, tolerance
            )

        matched = DataComparator._normalize(expected) == DataComparator._normalize(actual)
        message = f"{field_name}: match" if matched else f"{field_name}: {expected!r} != {actual!r}"
        return FieldComparison(
            field=field_name,
            expected=expected,
            actual=actual,
            comparison_type="exact",
            matched=matched,
            message=message,
        )

    @staticmethod
    def _compare_numeric_with_tolerance(
        field_name: str, expected: float, actual: float, tolerance: Tolerance
    ) -> FieldComparison:
        difference = abs(actual - expected)
        difference_pct: float | None = None
        checks: list[bool] = []
        comparison_labels: list[str] = []
        failure_parts: list[str] = []

        if tolerance.percentage is not None:
            comparison_labels.append("percentage")
            if expected == 0:
                # A percentage of zero is zero — only an exact match can
                # satisfy a percentage-only tolerance here; pair it with
                # `absolute=` to allow a real margin around a zero baseline.
                pct_ok = actual == expected
                failure_parts.append(
                    "percentage tolerance is undefined for an expected value of 0 "
                    f"(actual={actual!r}); add absolute= for a zero baseline"
                )
            else:
                difference_pct = (difference / abs(expected)) * 100
                pct_ok = difference_pct <= tolerance.percentage
                failure_parts.append(f"{difference_pct:.4f}% > {tolerance.percentage}% tolerance")
            checks.append(pct_ok)

        if tolerance.absolute is not None:
            comparison_labels.append("absolute")
            abs_ok = difference <= tolerance.absolute
            checks.append(abs_ok)
            failure_parts.append(f"{difference!r} > {tolerance.absolute!r} absolute tolerance")

        matched = any(checks)
        comparison_type = (
            "_or_".join(comparison_labels) + "_tolerance"
            if len(comparison_labels) > 1
            else f"{comparison_labels[0]}_tolerance"
        )

        if matched:
            message = f"{field_name}: {actual!r} within tolerance of expected {expected!r}"
        else:
            message = (
                f"{field_name}: {actual!r} outside tolerance of expected {expected!r} "
                f"({'; '.join(failure_parts)})"
            )

        return FieldComparison(
            field=field_name,
            expected=expected,
            actual=actual,
            comparison_type=comparison_type,
            matched=matched,
            tolerance=tolerance,
            difference=difference,
            difference_pct=difference_pct,
            message=message,
        )

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @staticmethod
    def compare_ui_api(
        ui: dict[str, Any],
        api: dict[str, Any],
        *,
        fields: list[str] | None = None,
        tolerance: Tolerance | None = None,
    ) -> ComparisonResult:
        return DataComparator.compare(
            ui, api, left_label="UI", right_label="API", fields=fields, tolerance=tolerance
        )

    @staticmethod
    def compare_api_db(
        api: dict[str, Any],
        db: dict[str, Any],
        *,
        fields: list[str] | None = None,
        tolerance: Tolerance | None = None,
    ) -> ComparisonResult:
        return DataComparator.compare(
            api, db, left_label="API", right_label="Database", fields=fields, tolerance=tolerance
        )

    @staticmethod
    def compare_ui_db(
        ui: dict[str, Any],
        db: dict[str, Any],
        *,
        fields: list[str] | None = None,
        tolerance: Tolerance | None = None,
    ) -> ComparisonResult:
        return DataComparator.compare(
            ui, db, left_label="UI", right_label="Database", fields=fields, tolerance=tolerance
        )

    @staticmethod
    def compare_all(
        ui: dict[str, Any],
        api: dict[str, Any],
        db: dict[str, Any],
        *,
        fields: list[str] | None = None,
        tolerance: Tolerance | None = None,
    ) -> list[ComparisonResult]:
        """UI<->API, API<->DB, UI<->DB — three pairwise comparisons that
        together prove all three layers agree (agreeing pairwise is
        equivalent to all three matching, and pinpoints *which* pair
        diverges when they don't).
        """
        return [
            DataComparator.compare_ui_api(ui, api, fields=fields, tolerance=tolerance),
            DataComparator.compare_api_db(api, db, fields=fields, tolerance=tolerance),
            DataComparator.compare_ui_db(ui, db, fields=fields, tolerance=tolerance),
        ]
