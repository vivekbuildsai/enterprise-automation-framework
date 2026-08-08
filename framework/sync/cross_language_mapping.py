"""Concept-level migration guidance — a small, curated, evidence-based
table, never a generated/fabricated one. `lookup_cross_language_mappings`
only ever returns entries for technologies/structural elements the
analyzer actually detected in the target repository; nothing here claims
automatic conversion (see `SyncMode.MIGRATE`'s docstring and
docs/FrameworkSync.md, "Compatibility model").

Every target technology here is this framework's own stack (Playwright +
pytest + `framework.api.ApiClient`) — the one real, actionable migration
target this product can meaningfully guide a customer toward.
"""

from __future__ import annotations

from framework.sync.models import CrossLanguageMapping, MappingStatus, RepositoryAnalysis

_TECHNOLOGY_MAPPINGS: dict[str, list[CrossLanguageMapping]] = {
    "Selenium": [
        CrossLanguageMapping(
            source_technology="Selenium",
            concept="Browser element interaction (WebDriver.find_element/click/send_keys)",
            target_technology="Playwright Page/Locator",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Review locator strategy and explicit-wait usage — Playwright's "
                "auto-waiting changes the semantics, not just the syntax."
            ),
        )
    ],
    "Cypress": [
        CrossLanguageMapping(
            source_technology="Cypress",
            concept="Chained browser commands (cy.visit/cy.get/cy.click)",
            target_technology="Playwright Page/Locator",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite as explicit Page Object methods — Cypress's implicit "
                "retry/chaining has no direct syntactic equivalent."
            ),
        )
    ],
    "WebdriverIO": [
        CrossLanguageMapping(
            source_technology="WebdriverIO",
            concept="WebDriver-protocol browser interaction",
            target_technology="Playwright Page/Locator",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite as Page Object methods — WebdriverIO's async/await JS "
                "model has no direct Python equivalent."
            ),
        )
    ],
    "TestNG": [
        CrossLanguageMapping(
            source_technology="TestNG",
            concept="Java annotation-driven test class",
            target_technology="pytest",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite test classes as pytest functions/classes; map "
                "@DataProvider to pytest.mark.parametrize, "
                "@BeforeMethod/@AfterMethod to fixtures."
            ),
        )
    ],
    "JUnit": [
        CrossLanguageMapping(
            source_technology="JUnit",
            concept="Java annotation-driven test class",
            target_technology="pytest",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite test classes as pytest functions/classes; map "
                "@Before/@After to fixtures."
            ),
        )
    ],
    "NUnit": [
        CrossLanguageMapping(
            source_technology="NUnit",
            concept="C# attribute-driven test class",
            target_technology="pytest",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite test classes as pytest functions/classes; map "
                "[SetUp]/[TearDown] to fixtures, [TestCase] to pytest.mark.parametrize."
            ),
        )
    ],
    "xUnit": [
        CrossLanguageMapping(
            source_technology="xUnit",
            concept="C# attribute-driven test class",
            target_technology="pytest",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite test classes as pytest functions; map [Theory]/[InlineData] "
                "to pytest.mark.parametrize."
            ),
        )
    ],
    "Robot Framework SeleniumLibrary": [
        CrossLanguageMapping(
            source_technology="Robot Framework SeleniumLibrary",
            concept="Keyword-driven browser interaction (Open Browser, Input Text, Click Button)",
            target_technology="Playwright Page/Locator",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Review locator strategy and lifecycle semantics — each keyword maps "
                "to a Page Object method, not a mechanical 1:1 call."
            ),
        )
    ],
    "Robot Framework Browser Library": [
        CrossLanguageMapping(
            source_technology="Robot Framework Browser Library",
            concept="Keyword-driven browser interaction (already Playwright-based)",
            target_technology="Playwright Page/Locator",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Closest of all Robot UI libraries to this framework's own engine — "
                "still requires rewriting keywords as Page Object methods, not a "
                "mechanical port."
            ),
        )
    ],
    "Robot Framework RequestsLibrary": [
        CrossLanguageMapping(
            source_technology="Robot Framework RequestsLibrary",
            concept="Keyword-driven HTTP API testing (Create Session, GET/POST On Session)",
            target_technology="framework.api.ApiClient",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite session/request keywords as ApiClient calls; response "
                "assertions map to framework.assertions."
            ),
        )
    ],
}

# Robot's *structural* concepts (Test Cases/Keywords/Resources/Variables/
# Setup/Teardown) aren't `DetectedFramework` entries — they come from
# `RobotStructure` — so they're looked up separately, gated on the actual
# count/flag being non-zero/true (never emitted for a structure that
# wasn't observed).
_ROBOT_COUNT_MAPPINGS: tuple[tuple[str, CrossLanguageMapping], ...] = (
    (
        "test_case_count",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Test Case",
            target_technology="pytest test function",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action="One Robot Test Case becomes one pytest test function/method.",
        ),
    ),
    (
        "keyword_count",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="User-defined Keyword",
            target_technology="Python helper/Page-Object/component method",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Rewrite each Keyword as a method on the corresponding "
                "Page Object/component/helper class."
            ),
        ),
    ),
    (
        "resource_file_count",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Resource file",
            target_technology="Page Object / component / helper module",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Split shared Keywords by responsibility into Page Object/component "
                "modules — not a single 1:1 file port."
            ),
        ),
    ),
    (
        "variable_count",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Variables",
            target_technology="config/environments/*.yaml + .env / test-data source",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Split by purpose: environment-specific values into config YAML/.env, "
                "test data into framework.testdata."
            ),
        ),
    ),
)

_ROBOT_FLAG_MAPPINGS: tuple[tuple[str, CrossLanguageMapping], ...] = (
    (
        "has_suite_setup",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Suite Setup",
            target_technology="pytest session/module-scoped fixture",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action="Move Suite Setup logic into a session/module-scoped pytest fixture.",
        ),
    ),
    (
        "has_suite_teardown",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Suite Teardown",
            target_technology="pytest fixture teardown (post-yield)",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Move Suite Teardown logic to the code after `yield` in the matching fixture."
            ),
        ),
    ),
    (
        "has_test_setup",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Test Setup",
            target_technology="pytest function-scoped fixture",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action="Move Test Setup logic into a function-scoped pytest fixture.",
        ),
    ),
    (
        "has_test_teardown",
        CrossLanguageMapping(
            source_technology="Robot Framework",
            concept="Test Teardown",
            target_technology="pytest fixture teardown (post-yield)",
            status=MappingStatus.CONCEPTUALLY_MAPPABLE,
            manual_action=(
                "Move Test Teardown logic to the code after `yield` in the matching fixture."
            ),
        ),
    ),
)


def lookup_cross_language_mappings(analysis: RepositoryAnalysis) -> list[CrossLanguageMapping]:
    """Evidence-based only: a mapping is returned if and only if the
    corresponding technology/structural element was actually detected in
    `analysis`. An undetected technology yields nothing — never a
    speculative/default mapping.
    """
    mappings: list[CrossLanguageMapping] = []

    for framework in analysis.detected_frameworks:
        mappings.extend(_TECHNOLOGY_MAPPINGS.get(framework.name, []))

    robot = analysis.robot_structure
    if robot is not None:
        for field_name, mapping in _ROBOT_COUNT_MAPPINGS:
            if getattr(robot, field_name) > 0:
                mappings.append(mapping)
        for field_name, mapping in _ROBOT_FLAG_MAPPINGS:
            if getattr(robot, field_name):
                mappings.append(mapping)

    return mappings
