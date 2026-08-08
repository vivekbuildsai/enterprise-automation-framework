"""Robot Framework structural analysis — Test Cases, Keywords, Resource
files, Libraries, Variables, Setup/Teardown — verified against the
`.robot`/`.resource` fixtures under tests/sync/fixtures/, plus
`framework.sync.robot_analysis` unit-level (no repository needed).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.robot_analysis import analyze_robot_file, merge_robot_structures

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_robot_selenium_library_fixture_structure() -> None:
    root = _FIXTURES / "robot_selenium_library"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))
    robot = analysis.robot_structure

    assert robot is not None
    assert robot.test_case_count == 2  # "Valid Login", "Invalid Login Shows Error"
    assert robot.keyword_count == 2  # "Open Browser To Login Page", "Login As Standard User"
    assert robot.resource_file_count == 1  # common.resource
    assert robot.variable_count == 2  # ${URL}, ${BROWSER}
    assert "SeleniumLibrary" in robot.library_names
    assert robot.has_suite_setup is True
    assert robot.has_suite_teardown is True
    assert robot.has_test_setup is False
    assert robot.has_test_teardown is False


def test_robot_browser_library_fixture_structure() -> None:
    root = _FIXTURES / "robot_browser_library"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))
    robot = analysis.robot_structure

    assert robot is not None
    assert robot.test_case_count == 1
    assert robot.resource_file_count == 0
    assert "Browser" in robot.library_names
    assert robot.has_test_setup is True
    assert robot.has_suite_setup is False


def test_robot_requests_library_fixture_structure() -> None:
    root = _FIXTURES / "robot_requests_library"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))
    robot = analysis.robot_structure

    assert robot is not None
    assert robot.test_case_count == 1
    assert "RequestsLibrary" in robot.library_names


def test_repository_without_robot_files_has_no_robot_structure() -> None:
    root = _FIXTURES / "typescript_playwright"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    assert analysis.robot_structure is None


# -- framework.sync.robot_analysis unit-level (no repository needed) -----


def test_analyze_robot_file_counts_test_cases_and_keywords() -> None:
    text = (
        "*** Test Cases ***\n"
        "First Test\n"
        "    Log    hello\n"
        "Second Test\n"
        "    Log    world\n"
        "*** Keywords ***\n"
        "My Keyword\n"
        "    Log    from keyword\n"
    )
    structure = analyze_robot_file(text)

    assert structure.test_case_count == 2
    assert structure.keyword_count == 1


def test_analyze_robot_file_ignores_indented_steps_as_new_items() -> None:
    """Robot's own convention: only a column-0 line starts a new Test
    Case/Keyword — indented lines under it are its steps, never counted
    as separate items.
    """
    text = "*** Test Cases ***\nOnly One Test\n    Step One\n    Step Two\n    Step Three\n"
    structure = analyze_robot_file(text)

    assert structure.test_case_count == 1


def test_analyze_robot_file_captures_libraries_and_lifecycle() -> None:
    text = (
        "*** Settings ***\n"
        "Library    SeleniumLibrary\n"
        "Library    Collections\n"
        "Suite Setup    Do Setup\n"
        "Test Teardown    Do Teardown\n"
    )
    structure = analyze_robot_file(text)

    assert structure.library_names == ["SeleniumLibrary", "Collections"]
    assert structure.has_suite_setup is True
    assert structure.has_test_teardown is True
    assert structure.has_suite_teardown is False
    assert structure.has_test_setup is False


def test_analyze_robot_file_counts_variables() -> None:
    text = "*** Variables ***\n${URL}    https://example.test\n@{LIST}    a    b    c\n"
    structure = analyze_robot_file(text)

    assert structure.variable_count == 2


def test_analyze_robot_file_handles_empty_and_unrecognized_content_without_crashing() -> None:
    assert analyze_robot_file("").test_case_count == 0
    assert analyze_robot_file("just some prose, no sections at all\n").test_case_count == 0


def test_merge_robot_structures_sums_counts_and_dedupes_libraries() -> None:
    first = analyze_robot_file("*** Settings ***\nLibrary    SeleniumLibrary\n")
    second = analyze_robot_file(
        "*** Settings ***\nLibrary    SeleniumLibrary\nLibrary    Collections\n"
    )

    merged = merge_robot_structures([first, second])

    assert merged.library_names == ["SeleniumLibrary", "Collections"]
