"""Detects which of the customer's own automation ecosystems new-UI
scaffold code should be written in — reuses `RepositoryAnalysis` (the
existing Framework Sync output: `primary_language` + `detected_frameworks`
+ `robot_structure`) rather than re-scanning source a second time. This is
the one decision point requirement #9 ("framework-native scaffolding")
depends on: never generate Python code for a Java customer, never guess a
target when the evidence doesn't clearly support one.
"""

from __future__ import annotations

from framework.extension.models import ScaffoldTarget
from framework.sync.models import RepositoryAnalysis


def detect_scaffold_target(analysis: RepositoryAnalysis) -> ScaffoldTarget:
    """Robot Framework is checked first — it's detected by `.robot`/
    `.resource` files existing at all (see `RobotFrameworkAdapter`), which
    is strong enough evidence to take priority even if `primary_language`
    happens to be Python (Robot suites are commonly paired with Python
    libraries). Every other target requires *both* the primary language
    and its paired UI-automation/test-runner technology to be detected —
    a bare language match alone (e.g. "Java" with no TestNG/JUnit
    evidence) is not enough to pick a target.
    """
    names = {framework.name for framework in analysis.detected_frameworks}

    if analysis.robot_structure is not None or "Robot Framework" in names:
        return ScaffoldTarget.ROBOT_FRAMEWORK

    language = analysis.primary_language
    if language == "Java" and "TestNG" in names:
        return ScaffoldTarget.JAVA_SELENIUM_TESTNG
    if language == "Java" and "JUnit" in names:
        return ScaffoldTarget.JAVA_SELENIUM_JUNIT
    if language == "Python" and "pytest" in names and "Playwright" in names:
        return ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT
    if language == "TypeScript" and "Playwright" in names:
        return ScaffoldTarget.TYPESCRIPT_PLAYWRIGHT

    return ScaffoldTarget.UNKNOWN
