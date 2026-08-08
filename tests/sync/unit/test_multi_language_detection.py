"""Language/framework/runner/dependency detection across every P0/P1
technology this milestone adds — one real, sanitized fixture per
language/framework combination under tests/sync/fixtures/ (never executed,
only statically analyzed — see tests/sync/fixtures/conftest.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer, SupportLevel

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def _analyze(fixture_name: str):
    root = _FIXTURES / fixture_name
    return RepositoryAnalyzer().analyze(root, source=str(root))


def _names(analysis) -> set[str]:
    return {f.name for f in analysis.detected_frameworks}


# -- A: Java + Selenium + TestNG ------------------------------------------


def test_java_selenium_testng_language_and_frameworks() -> None:
    analysis = _analyze("java_selenium_testng")

    assert analysis.primary_language == "Java"
    assert "pom.xml" in analysis.structure.dependency_files
    assert "Selenium" in _names(analysis)
    assert "TestNG" in _names(analysis)

    testng = next(f for f in analysis.detected_frameworks if f.name == "TestNG")
    assert testng.category == "test_runner"
    assert testng.support_level == SupportLevel.REQUIRES_MANUAL_REVIEW
    assert testng.evidence


# -- B: Java + Selenium + JUnit --------------------------------------------


def test_java_selenium_junit_language_and_frameworks() -> None:
    analysis = _analyze("java_selenium_junit")

    assert analysis.primary_language == "Java"
    assert "Selenium" in _names(analysis)
    assert "JUnit" in _names(analysis)

    junit = next(f for f in analysis.detected_frameworks if f.name == "JUnit")
    assert junit.support_level == SupportLevel.REQUIRES_MANUAL_REVIEW


# -- C: TypeScript + Playwright ---------------------------------------------


def test_typescript_playwright_language_and_framework() -> None:
    analysis = _analyze("typescript_playwright")

    assert analysis.primary_language == "TypeScript"
    assert "package.json" in analysis.structure.dependency_files
    assert "Playwright" in _names(analysis)

    playwright = next(f for f in analysis.detected_frameworks if f.name == "Playwright")
    assert playwright.support_level == SupportLevel.SUPPORTED


# -- D: TypeScript + Cypress --------------------------------------------


def test_typescript_cypress_language_and_framework() -> None:
    analysis = _analyze("typescript_cypress")

    assert analysis.primary_language == "TypeScript"
    assert "Cypress" in _names(analysis)

    cypress = next(f for f in analysis.detected_frameworks if f.name == "Cypress")
    assert cypress.support_level == SupportLevel.PARTIALLY_SUPPORTED


# -- E: Python + pytest + Playwright --------------------------------------


def test_python_pytest_playwright_language_and_frameworks() -> None:
    analysis = _analyze("python_pytest_playwright")

    assert analysis.primary_language == "Python"
    assert "Playwright" in _names(analysis)
    assert "pytest" in _names(analysis)


# -- F: Python + Selenium (no pytest runner) -------------------------------


def test_python_selenium_language_and_framework() -> None:
    analysis = _analyze("python_selenium")

    assert analysis.primary_language == "Python"
    assert "Selenium" in _names(analysis)
    # Deliberately unittest-based, not pytest-based — proves the pytest
    # adapter doesn't fire on every Python repository indiscriminately.
    assert "pytest" not in _names(analysis)


# -- G: C# + Selenium + NUnit ----------------------------------------------


def test_csharp_selenium_nunit_language_and_frameworks() -> None:
    analysis = _analyze("csharp_selenium_nunit")

    assert analysis.primary_language == "C#"
    assert any(f.endswith(".csproj") for f in analysis.structure.dependency_files)
    assert "Selenium" in _names(analysis)
    assert "NUnit" in _names(analysis)

    nunit = next(f for f in analysis.detected_frameworks if f.name == "NUnit")
    assert nunit.category == "test_runner"
    assert nunit.support_level == SupportLevel.REQUIRES_MANUAL_REVIEW


# -- H/I/J: Robot Framework (SeleniumLibrary/Browser/RequestsLibrary) -----


def test_robot_selenium_library_detected() -> None:
    analysis = _analyze("robot_selenium_library")

    assert analysis.primary_language == "Robot Framework"
    assert "Robot Framework" in _names(analysis)
    assert "Robot Framework SeleniumLibrary" in _names(analysis)

    seleniumlibrary = next(
        f for f in analysis.detected_frameworks if f.name == "Robot Framework SeleniumLibrary"
    )
    assert seleniumlibrary.category == "ui_automation"
    assert seleniumlibrary.support_level == SupportLevel.PARTIALLY_SUPPORTED


def test_robot_browser_library_detected() -> None:
    analysis = _analyze("robot_browser_library")

    assert "Robot Framework Browser Library" in _names(analysis)
    browser = next(
        f for f in analysis.detected_frameworks if f.name == "Robot Framework Browser Library"
    )
    assert browser.category == "ui_automation"
    assert browser.support_level == SupportLevel.PARTIALLY_SUPPORTED
    # Not falsely detected as SeleniumLibrary too.
    assert "Robot Framework SeleniumLibrary" not in _names(analysis)


def test_robot_requests_library_detected() -> None:
    analysis = _analyze("robot_requests_library")

    assert "Robot Framework RequestsLibrary" in _names(analysis)
    requests_lib = next(
        f for f in analysis.detected_frameworks if f.name == "Robot Framework RequestsLibrary"
    )
    assert requests_lib.category == "api_automation"
    assert requests_lib.support_level == SupportLevel.PARTIALLY_SUPPORTED


# -- Additional P0/P1 technologies not covered by a lettered fixture -----


def test_webdriverio_detected_from_config_and_dependency_evidence(tmp_path: Path) -> None:
    (tmp_path / "wdio.conf.ts").write_text("export const config = {}\n")
    (tmp_path / "package.json").write_text('{"devDependencies": {"@wdio/cli": "^8.0.0"}}\n')

    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert "WebdriverIO" in _names(analysis)


def test_xunit_detected_via_fact_attribute(tmp_path: Path) -> None:
    (tmp_path / "Tests.cs").write_text(
        "using Xunit;\n\npublic class T {\n    [Fact]\n    public void Test1() {}\n}\n"
    )

    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert "xUnit" in _names(analysis)


def test_csharp_playwright_detected_despite_case_difference(tmp_path: Path) -> None:
    """`Microsoft.Playwright` (capital P) previously wasn't detected by
    the generic Playwright adapter, which only matched lowercase
    `playwright` — a real, evidence-based gap fixed by making `_matches`
    case-insensitive (see framework/sync/detectors.py).
    """
    (tmp_path / "Tests.cs").write_text("using Microsoft.Playwright;\n")

    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert "Playwright" in _names(analysis)


def test_csharp_selenium_detected_despite_case_difference(tmp_path: Path) -> None:
    """`OpenQA.Selenium` (capital O/S) previously wasn't detected — same
    case-sensitivity gap as Playwright above.
    """
    (tmp_path / "Tests.cs").write_text("using OpenQA.Selenium;\n")

    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert "Selenium" in _names(analysis)
