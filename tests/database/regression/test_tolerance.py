from __future__ import annotations

import pytest

from framework.database.utilities import DataComparator, Tolerance

pytestmark = [pytest.mark.regression, pytest.mark.database]


def _compare(expected: dict, actual: dict, tolerance: Tolerance) -> object:
    return DataComparator.compare(
        expected, actual, left_label="Expected", right_label="Actual", tolerance=tolerance
    )


class TestPercentageTolerance:
    def test_within_tolerance_passes(self) -> None:
        """Expected 1000, actual 1005, tolerance 1% -> 0.5% difference -> PASS."""
        result = _compare({"total": 1000}, {"total": 1005}, Tolerance(percentage=1.0))
        assert result.matched
        fc = result.field_comparisons[0]
        assert fc.matched
        assert fc.comparison_type == "percentage_tolerance"
        assert fc.difference_pct == pytest.approx(0.5)

    def test_outside_tolerance_fails(self) -> None:
        """Expected 1000, actual 1020, tolerance 1% -> 2% difference -> FAIL."""
        result = _compare({"total": 1000}, {"total": 1020}, Tolerance(percentage=1.0))
        assert not result.matched
        fc = result.field_comparisons[0]
        assert not fc.matched
        assert fc.difference_pct == pytest.approx(2.0)
        assert "2.0000% > 1.0% tolerance" in fc.message

    def test_exactly_at_the_boundary_passes(self) -> None:
        """The tolerance check is inclusive (<=), not strict (<)."""
        result = _compare({"total": 1000}, {"total": 1010}, Tolerance(percentage=1.0))
        assert result.matched

    def test_negative_values(self) -> None:
        result = _compare({"delta": -1000}, {"delta": -1005}, Tolerance(percentage=1.0))
        assert result.matched
        assert result.field_comparisons[0].difference_pct == pytest.approx(0.5)

    def test_float_values(self) -> None:
        result = _compare({"rate": 10.0}, {"rate": 10.05}, Tolerance(percentage=1.0))
        assert result.matched

    def test_integer_and_float_mix(self) -> None:
        result = _compare({"total": 1000}, {"total": 1005.0}, Tolerance(percentage=1.0))
        assert result.matched
        assert result.field_comparisons[0].comparison_type == "percentage_tolerance"

    def test_zero_expected_with_zero_actual_passes(self) -> None:
        result = _compare({"total": 0}, {"total": 0}, Tolerance(percentage=1.0))
        assert result.matched

    def test_zero_expected_with_nonzero_actual_fails_without_absolute_tolerance(self) -> None:
        """A percentage of zero is zero — only an exact match satisfies a
        percentage-only tolerance against a zero baseline.
        """
        result = _compare({"total": 0}, {"total": 1}, Tolerance(percentage=1.0))
        assert not result.matched
        fc = result.field_comparisons[0]
        assert fc.difference_pct is None
        assert "undefined" in fc.message.lower()


class TestAbsoluteTolerance:
    def test_within_absolute_tolerance_passes(self) -> None:
        result = _compare({"count": 1000}, {"count": 1003}, Tolerance(absolute=5))
        assert result.matched
        assert result.field_comparisons[0].comparison_type == "absolute_tolerance"
        assert result.field_comparisons[0].difference == 3

    def test_outside_absolute_tolerance_fails(self) -> None:
        result = _compare({"count": 1000}, {"count": 1010}, Tolerance(absolute=5))
        assert not result.matched
        assert (
            "5 > 5" not in result.field_comparisons[0].message
        )  # sanity: not a boundary false-fail

    def test_zero_expected_with_absolute_tolerance_allows_a_real_margin(self) -> None:
        """The case percentage tolerance can't express cleanly — pairing a
        zero-ish baseline with an absolute tolerance instead.
        """
        result = _compare({"count": 0}, {"count": 2}, Tolerance(absolute=5))
        assert result.matched

    def test_negative_values_with_absolute_tolerance(self) -> None:
        result = _compare({"delta": -100}, {"delta": -103}, Tolerance(absolute=5))
        assert result.matched


class TestCombinedTolerance:
    def test_passes_if_either_percentage_or_absolute_is_satisfied(self) -> None:
        # 1% of 10 is 0.1 (fails), but absolute=1 covers a diff of 1.
        result = _compare({"total": 10}, {"total": 11}, Tolerance(percentage=1.0, absolute=1))
        assert result.matched
        assert result.field_comparisons[0].comparison_type == "percentage_or_absolute_tolerance"

    def test_fails_when_neither_is_satisfied(self) -> None:
        result = _compare({"total": 10}, {"total": 100}, Tolerance(percentage=1.0, absolute=1))
        assert not result.matched


class TestExactComparisonUnaffectedByTolerance:
    def test_non_numeric_fields_still_use_exact_normalized_comparison(self) -> None:
        result = _compare(
            {"status": "ACTIVE", "total": 1000},
            {"status": "active", "total": 1005},
            Tolerance(percentage=1.0),
        )
        assert result.matched
        status_fc = next(fc for fc in result.field_comparisons if fc.field == "status")
        assert status_fc.comparison_type == "exact"

    def test_no_tolerance_argument_means_exact_comparison_as_before(self) -> None:
        result = DataComparator.compare(
            {"total": 1000}, {"total": 1005}, left_label="Expected", right_label="Actual"
        )
        assert not result.matched


class TestNullHandling:
    def test_both_none_matches_even_with_tolerance_configured(self) -> None:
        result = _compare({"total": None}, {"total": None}, Tolerance(percentage=1.0))
        assert result.matched
        assert result.field_comparisons[0].comparison_type == "exact"

    def test_expected_none_actual_present_is_a_mismatch(self) -> None:
        result = _compare({"total": None}, {"total": 1000}, Tolerance(percentage=1.0))
        assert not result.matched

    def test_expected_present_actual_none_is_a_mismatch(self) -> None:
        result = _compare({"total": 1000}, {"total": None}, Tolerance(percentage=1.0))
        assert not result.matched


class TestToleranceValidation:
    def test_tolerance_requires_at_least_one_bound(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            Tolerance()


class TestResultReporting:
    def test_to_report_includes_tolerance_failure_detail(self) -> None:
        result = _compare({"total": 1000}, {"total": 1020}, Tolerance(percentage=1.0))
        report = result.to_report()
        assert "MISMATCH" in report
        assert "total" in report
        assert "tolerance" in report.lower()

    def test_field_comparisons_populated_for_every_field_not_just_mismatches(self) -> None:
        result = _compare(
            {"total": 1000, "count": 5}, {"total": 1005, "count": 5}, Tolerance(percentage=1.0)
        )
        assert len(result.field_comparisons) == 2
        assert all(fc.matched for fc in result.field_comparisons)

    def test_raise_if_mismatched_still_works_with_tolerance(self) -> None:
        from framework.database.exceptions import DataComparisonError

        result = _compare({"total": 1000}, {"total": 2000}, Tolerance(percentage=1.0))
        with pytest.raises(DataComparisonError):
            result.raise_if_mismatched()


class TestCompareAllWithTolerance:
    def test_compare_all_accepts_and_applies_tolerance(self) -> None:
        results = DataComparator.compare_all(
            {"total": 1000}, {"total": 1003}, {"total": 1004}, tolerance=Tolerance(percentage=1.0)
        )
        assert all(r.matched for r in results)
