"""Test-level (not file-level) inventory extraction — the core evidence
requirement: a source file is never counted as a test merely because it
exists. See tests/sync/fixtures/ for the sanitized multi-test fixtures
used here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.models import TestCategory
from framework.sync.test_inventory import classify_test, extract_tests

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def _tests_for(fixture_name: str):
    root = _FIXTURES / fixture_name
    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(root)
    contents = analyzer._read_text_files(files)
    return extract_tests(root, contents)


def test_testng_extracts_annotated_methods_with_groups_and_class() -> None:
    tests = _tests_for("java_selenium_testng")

    assert len(tests) == 3
    by_name = {t.name: t for t in tests}
    assert by_name["validLoginReachesSecureArea"].class_name == "LoginTest"
    assert by_name["validLoginReachesSecureArea"].technology == "TestNG"
    assert set(by_name["validLoginReachesSecureArea"].tags) == {"smoke", "ui"}
    assert by_name["dashboardShowsWelcomeMessage"].class_name == "DashboardTest"


def test_testng_identifier_traces_back_to_exact_source() -> None:
    tests = _tests_for("java_selenium_testng")
    identifiers = {t.identifier for t in tests}

    assert "src/test/java/LoginTest.java::LoginTest::validLoginReachesSecureArea" in identifiers


def test_junit_extracts_methods_without_groups() -> None:
    tests = _tests_for("java_selenium_junit")

    assert len(tests) == 2
    assert all(t.technology == "JUnit" for t in tests)
    assert all(t.tags == [] for t in tests)


def test_pytest_extracts_functions_and_class_methods_with_markers() -> None:
    tests = _tests_for("python_pytest_playwright")

    assert len(tests) == 3
    by_name = {t.name: t for t in tests}
    assert by_name["test_valid_login_reaches_secure_area"].tags == ["smoke"]
    assert by_name["test_dashboard_shows_welcome_message"].class_name == "TestDashboard"


def test_playwright_extracts_tests_with_describe_and_tags() -> None:
    tests = _tests_for("typescript_playwright")

    assert len(tests) == 2
    by_name = {t.name: t for t in tests}
    assert by_name["valid login reaches secure area"].class_name == "login"
    assert by_name["valid login reaches secure area"].tags == ["smoke"]


def test_cypress_extracts_it_blocks_with_describe_but_no_tags() -> None:
    tests = _tests_for("typescript_cypress")

    assert len(tests) == 2
    assert all(t.tags == [] for t in tests)
    assert all(t.class_name == "login" for t in tests)


def test_robot_extracts_test_cases_with_tags() -> None:
    tests = _tests_for("robot_selenium_library")

    assert len(tests) == 2
    by_name = {t.name: t for t in tests}
    assert by_name["Valid Login"].tags == ["smoke"]
    assert by_name["Invalid Login Shows Error"].tags == ["regression"]


def test_a_repository_with_no_recognized_test_syntax_yields_zero_tests(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("# Notes\nNo test code here.\n")
    (tmp_path / "Config.cs").write_text("public class Config {}\n")  # no [Test] attribute at all

    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(tmp_path)
    contents = analyzer._read_text_files(files)

    assert extract_tests(tmp_path, contents) == []


def test_source_file_presence_alone_never_counts_as_a_test(tmp_path: Path) -> None:
    """A `.java` file that imports Selenium/TestNG but has no `@Test`
    annotation at all is not a test — mirrors the milestone's explicit
    requirement: never claim a file is a test merely because it exists.
    """
    (tmp_path / "PageHelper.java").write_text(
        "package com.example;\n\n"
        "import org.testng.annotations.Test;\n\n"
        "public class PageHelper {\n"
        "    public void notATestMethod() {}\n"
        "}\n"
    )
    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(tmp_path)
    contents = analyzer._read_text_files(files)

    assert extract_tests(tmp_path, contents) == []


# -- Category classification -----------------------------------------------


def test_classify_test_prefers_tag_evidence_over_layer_evidence() -> None:
    category = classify_test(["smoke"], "import selenium\nimport requests\n")
    assert category == TestCategory.SMOKE


def test_classify_test_falls_back_to_layer_combination() -> None:
    assert classify_test([], "from selenium import webdriver") == TestCategory.UI
    assert classify_test([], "import requests\nrequests.get(x)") == TestCategory.API
    assert (
        classify_test([], "cursor.execute('select 1')\nimport sqlalchemy") == TestCategory.DATABASE
    )
    assert classify_test([], "selenium\nimport requests\nrequests.get(x)") == TestCategory.UI_API


def test_classify_test_is_unknown_without_any_evidence() -> None:
    assert classify_test([], "print('hello')") == TestCategory.UNKNOWN


def test_classify_test_never_fabricates_a_category_from_an_unmapped_tag() -> None:
    assert classify_test(["some-custom-tag"], "print('nothing')") == TestCategory.UNKNOWN
