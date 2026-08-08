from __future__ import annotations

import pytest

from framework.database.exceptions import DataComparisonError
from framework.database.utilities import DataComparator

pytestmark = [pytest.mark.regression, pytest.mark.database]


def test_compare_matches_when_fields_are_equal_case_insensitively() -> None:
    result = DataComparator.compare(
        {"status": "ACTIVE", "cos": "Gold"},
        {"status": "Active", "cos": "gold"},
        left_label="Expected",
        right_label="Actual",
    )
    assert result.matched
    assert result.diffs == []


def test_compare_detects_mismatched_fields() -> None:
    result = DataComparator.compare(
        {"status": "ACTIVE"}, {"status": "SUSPENDED"}, left_label="Expected", right_label="Actual"
    )
    assert not result.matched
    assert result.diffs[0].field == "status"


def test_compare_defaults_to_intersection_of_keys() -> None:
    result = DataComparator.compare(
        {"a": 1, "b": 2}, {"a": 1, "c": 3}, left_label="L", right_label="R"
    )
    assert result.compared_fields == ["a"]
    assert result.matched


def test_compare_all_returns_three_pairwise_results() -> None:
    results = DataComparator.compare_all({"a": 1}, {"a": 1}, {"a": 1})
    assert len(results) == 3
    assert all(r.matched for r in results)
    assert [r.right_label for r in results] == ["API", "Database", "Database"]


def test_to_report_is_human_readable_on_mismatch() -> None:
    result = DataComparator.compare(
        {"cos": "Gold"},
        {"cos": "Silver"},
        left_label="Expected Subscriber",
        right_label="API Subscriber",
    )
    report = result.to_report()
    assert "MISMATCH" in report
    assert "cos" in report
    assert "Gold" in report
    assert "Silver" in report


def test_raise_if_mismatched_raises_data_comparison_error() -> None:
    result = DataComparator.compare({"a": 1}, {"a": 2}, left_label="L", right_label="R")
    with pytest.raises(DataComparisonError):
        result.raise_if_mismatched()


def test_raise_if_mismatched_is_a_no_op_on_match() -> None:
    result = DataComparator.compare({"a": 1}, {"a": 1}, left_label="L", right_label="R")
    result.raise_if_mismatched()  # must not raise
