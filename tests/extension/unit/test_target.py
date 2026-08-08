"""Scaffold target detection — must never generate code in the wrong
language. Reuses `RepositoryAnalysis` (already-detected language +
frameworks) rather than re-scanning source; `UNKNOWN` is a real, expected
outcome, not a bug, whenever the evidence doesn't clearly support one of
the five explicitly-supported combinations.
"""

from __future__ import annotations

import pytest

from framework.extension.models import ScaffoldTarget
from framework.extension.target import detect_scaffold_target
from framework.sync.models import (
    DetectedFramework,
    RepositoryAnalysis,
    RobotStructure,
    SupportLevel,
)

pytestmark = pytest.mark.extension


def _framework(name: str, category: str = "ui_automation") -> DetectedFramework:
    return DetectedFramework(name=name, category=category, support_level=SupportLevel.SUPPORTED)


def _analysis(
    *, language: str, frameworks: list[DetectedFramework], robot: RobotStructure | None = None
) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        source="test",
        primary_language=language,
        detected_frameworks=frameworks,
        robot_structure=robot,
    )


def test_java_selenium_testng_detected() -> None:
    analysis = _analysis(
        language="Java", frameworks=[_framework("Selenium"), _framework("TestNG", "test_runner")]
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.JAVA_SELENIUM_TESTNG


def test_java_selenium_junit_detected() -> None:
    analysis = _analysis(
        language="Java", frameworks=[_framework("Selenium"), _framework("JUnit", "test_runner")]
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.JAVA_SELENIUM_JUNIT


def test_java_with_both_testng_and_junit_prefers_testng() -> None:
    analysis = _analysis(
        language="Java",
        frameworks=[_framework("TestNG", "test_runner"), _framework("JUnit", "test_runner")],
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.JAVA_SELENIUM_TESTNG


def test_python_pytest_playwright_detected() -> None:
    analysis = _analysis(
        language="Python",
        frameworks=[_framework("Playwright"), _framework("pytest", "test_runner")],
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT


def test_typescript_playwright_detected() -> None:
    analysis = _analysis(language="TypeScript", frameworks=[_framework("Playwright")])
    assert detect_scaffold_target(analysis) == ScaffoldTarget.TYPESCRIPT_PLAYWRIGHT


def test_robot_framework_detected_via_robot_structure_even_with_python_primary_language() -> None:
    """Robot suites are commonly paired with Python libraries — the
    primary language being Python must never shadow real `.robot`/
    `.resource` evidence.
    """
    analysis = _analysis(language="Python", frameworks=[], robot=RobotStructure(test_case_count=3))
    assert detect_scaffold_target(analysis) == ScaffoldTarget.ROBOT_FRAMEWORK


def test_robot_framework_detected_via_detected_framework_name() -> None:
    analysis = _analysis(
        language="Python", frameworks=[_framework("Robot Framework", "automation_dsl")]
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.ROBOT_FRAMEWORK


def test_java_language_alone_without_a_test_runner_is_unknown() -> None:
    """A bare language match is never enough — real paired-technology
    evidence is required before a target is chosen.
    """
    analysis = _analysis(language="Java", frameworks=[_framework("Selenium")])
    assert detect_scaffold_target(analysis) == ScaffoldTarget.UNKNOWN


def test_csharp_is_unknown_no_supported_target() -> None:
    analysis = _analysis(
        language="C#", frameworks=[_framework("Selenium"), _framework("NUnit", "test_runner")]
    )
    assert detect_scaffold_target(analysis) == ScaffoldTarget.UNKNOWN


def test_no_detected_frameworks_at_all_is_unknown() -> None:
    analysis = _analysis(language="unknown", frameworks=[])
    assert detect_scaffold_target(analysis) == ScaffoldTarget.UNKNOWN
