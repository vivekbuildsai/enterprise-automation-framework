"""Scoped migration-candidate selection (Mode B, "Selective Migration")
and traceability — every candidate must trace back to its exact original
source, and status/reason must never claim a conversion actually
happened.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.exceptions import ConfigurationError
from framework.sync import RepositoryAnalyzer
from framework.sync.migration_candidates import select_migration_candidates
from framework.sync.models import MappingStatus, MigrationScope, RiskLevel

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def testng_analysis():
    root = _FIXTURES / "java_selenium_testng"
    return RepositoryAnalyzer().analyze(root, source=str(root))


def test_repository_scope_selects_every_detected_test(testng_analysis) -> None:
    candidates = select_migration_candidates(testng_analysis)
    assert len(candidates) == len(testng_analysis.tests) == 3


def test_directory_scope_selects_only_tests_under_the_given_prefix(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis, scope=MigrationScope.DIRECTORY, selector="src/test/java"
    )
    assert len(candidates) == 3
    assert all(c.test.source_file.startswith("src/test/java") for c in candidates)


def test_suite_scope_selects_only_tests_in_one_source_file(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis, scope=MigrationScope.SUITE, selector="src/test/java/DashboardTest.java"
    )
    assert len(candidates) == 1
    assert candidates[0].test.source_file == "src/test/java/DashboardTest.java"


def test_tag_scope_selects_only_tests_carrying_that_tag(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis, scope=MigrationScope.TAG, selector="smoke"
    )
    assert len(candidates) == 1
    assert "smoke" in candidates[0].test.tags


def test_class_scope_selects_only_tests_in_that_class(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis, scope=MigrationScope.CLASS, selector="DashboardTest"
    )
    assert len(candidates) == 1
    assert candidates[0].test.class_name == "DashboardTest"


def test_test_scope_selects_exactly_one_individual_test(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis,
        scope=MigrationScope.TEST,
        selector="src/test/java/LoginTest.java::LoginTest::validLoginReachesSecureArea",
    )
    assert len(candidates) == 1
    assert candidates[0].test.name == "validLoginReachesSecureArea"


def test_non_repository_scope_without_selector_raises_actionable_error(testng_analysis) -> None:
    with pytest.raises(ConfigurationError, match="requires a --selector"):
        select_migration_candidates(testng_analysis, scope=MigrationScope.TAG, selector=None)


def test_unmatched_selector_yields_zero_candidates_not_an_error(testng_analysis) -> None:
    candidates = select_migration_candidates(
        testng_analysis, scope=MigrationScope.TAG, selector="nonexistent-tag"
    )
    assert candidates == []


def test_selecting_a_subset_never_touches_the_rest_of_the_repository(testng_analysis) -> None:
    """MODE B's core guarantee: selecting one tag doesn't imply anything
    about the other tests — `analysis.tests` itself is never mutated by
    selection.
    """
    original_count = len(testng_analysis.tests)
    select_migration_candidates(testng_analysis, scope=MigrationScope.TAG, selector="smoke")
    assert len(testng_analysis.tests) == original_count


# -- Traceability + never "converted successfully" -------------------------


def test_every_candidate_carries_full_provenance(testng_analysis) -> None:
    candidates = select_migration_candidates(testng_analysis)
    for candidate in candidates:
        assert candidate.test.identifier
        assert candidate.test.source_file
        assert candidate.technology
        assert candidate.target_technology
        assert candidate.reason


def test_status_is_always_a_mapping_status_never_a_success_claim(testng_analysis) -> None:
    candidates = select_migration_candidates(testng_analysis)
    for candidate in candidates:
        assert isinstance(candidate.status, MappingStatus)
        assert "convert" not in candidate.reason.lower() or "not" in candidate.reason.lower()
        assert "successfully" not in candidate.reason.lower()


def test_risk_is_derived_deterministically_from_mapping_status(testng_analysis) -> None:
    candidates = select_migration_candidates(testng_analysis)
    for candidate in candidates:
        if candidate.status == MappingStatus.CONCEPTUALLY_MAPPABLE:
            assert candidate.risk == RiskLevel.MEDIUM
        elif candidate.status == MappingStatus.DIRECTLY_REUSABLE:
            assert candidate.risk == RiskLevel.LOW


def test_technology_already_matching_this_stack_is_directly_reusable() -> None:
    root = _FIXTURES / "python_pytest_playwright"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    candidates = select_migration_candidates(analysis)
    assert candidates  # pytest tests were actually extracted
    for candidate in candidates:
        assert candidate.status == MappingStatus.DIRECTLY_REUSABLE
        assert candidate.risk == RiskLevel.LOW
        assert "no migration needed" in candidate.reason.lower()
