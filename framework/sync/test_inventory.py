"""Test-level (not just file-level) inventory extraction — the answer to
"what do you already have?" (see docs/FrameworkSync.md, "Existing
customer test inventory"). A source file is never counted as a test
merely because it exists; every `Test` here is backed by
framework-specific evidence (an `@Test`/`@Test(...)` annotation, a
`def test_*`/`class Test*` function/class, a `test(...)`/`it(...)` call,
a Robot Test Case) found via the same lightweight regex/token scanning
`framework.sync.detectors` already uses — never execution, never a full
per-language parser.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from framework.sync.execution_model import detect_reporting_tools
from framework.sync.models import AutomationInventory, RobotStructure, Test, TestCategory
from framework.sync.robot_analysis import extract_robot_tests


class TestExtractor(Protocol):
    """Extracts individual `Test` entries for one technology's test
    syntax. Distinct from `FrameworkAdapter` (which only answers "is this
    technology present at all") — an extractor answers "exactly which
    tests exist, and what are they called."
    """

    technology: str

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]: ...


# ---------------------------------------------------------------------------
# Category classification — evidence-based, `UNKNOWN` when neither tier
# of evidence is available. Tags/markers/groups (explicit human intent)
# take priority over layer-inference (technology tokens present in the
# same source file).
# ---------------------------------------------------------------------------

_SUITE_TAG_MAP: dict[str, TestCategory] = {
    "smoke": TestCategory.SMOKE,
    "regression": TestCategory.REGRESSION,
    "integration": TestCategory.INTEGRATION,
    "unit": TestCategory.UNIT,
    "e2e": TestCategory.END_TO_END,
    "end_to_end": TestCategory.END_TO_END,
    "end-to-end": TestCategory.END_TO_END,
}

_UI_TOKENS = (
    "selenium",
    "webdriver",
    "playwright",
    "cypress",
    "cy.visit(",
    "cy.get(",
    "seleniumlibrary",
    "page.",
)
_API_TOKENS = (
    "requests.",
    "httpx.",
    "apiclient",
    "restassured",
    "fetch(",
    "axios",
    "requestslibrary",
    "on session",
)
_DB_TOKENS = ("sqlalchemy", "cursor.execute", "jdbc", "queryexecutor", "databasemanager")


def _category_from_tags(tags: list[str]) -> TestCategory | None:
    for tag in tags:
        if (category := _SUITE_TAG_MAP.get(tag.lower())) is not None:
            return category
    return None


_LAYER_COMBINATION_TO_CATEGORY: dict[tuple[bool, bool, bool], TestCategory] = {
    (True, True, True): TestCategory.END_TO_END,
    (True, True, False): TestCategory.UI_API,
    (True, False, True): TestCategory.UI_DATABASE,
    (False, True, True): TestCategory.API_DATABASE,
    (True, False, False): TestCategory.UI,
    (False, True, False): TestCategory.API,
    (False, False, True): TestCategory.DATABASE,
}


def _category_from_layers(file_text_lower: str) -> TestCategory | None:
    has_ui = any(token in file_text_lower for token in _UI_TOKENS)
    has_api = any(token in file_text_lower for token in _API_TOKENS)
    has_db = any(token in file_text_lower for token in _DB_TOKENS)
    return _LAYER_COMBINATION_TO_CATEGORY.get((has_ui, has_api, has_db))


def classify_test(tags: list[str], file_text: str) -> TestCategory:
    if (category := _category_from_tags(tags)) is not None:
        return category
    if (category := _category_from_layers(file_text.lower())) is not None:
        return category
    return TestCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Java (TestNG / JUnit) — both use the identical `@Test`/`@Test(...)`
# annotation syntax; the two are distinguished per-file by which runner's
# import is actually present (never guessed).
# ---------------------------------------------------------------------------

_JAVA_CLASS_PATTERN = re.compile(r"\bclass\s+(\w+)")
_JAVA_TEST_ANNOTATION_PATTERN = re.compile(r"@Test(\([^)]*\))?")
_JAVA_GROUPS_PATTERN = re.compile(r"groups\s*=\s*\{([^}]*)\}")
_JAVA_METHOD_PATTERN = re.compile(r"(?:public|private|protected)\s+[\w<>\[\],\s]+?\s+(\w+)\s*\(")


class JavaAnnotationTestExtractor:
    technology = "Java"

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]:
        tests: list[Test] = []
        for path, text in file_contents.items():
            if path.suffix != ".java":
                continue
            technology = self._runner_for_file(text)
            if technology is None:
                continue
            tests.extend(self._extract_from_file(root, path, text, technology))
        return tests

    @staticmethod
    def _runner_for_file(text: str) -> str | None:
        lowered = text.lower()
        if "org.testng" in lowered:
            return "TestNG"
        if "org.junit" in lowered:
            return "JUnit"
        return None

    @staticmethod
    def _extract_from_file(root: Path, path: Path, text: str, technology: str) -> list[Test]:
        relative = str(path.relative_to(root))
        lines = text.splitlines()
        current_class: str | None = None
        found: list[Test] = []

        for index, line in enumerate(lines):
            if class_match := _JAVA_CLASS_PATTERN.search(line):
                current_class = class_match.group(1)
            annotation_match = _JAVA_TEST_ANNOTATION_PATTERN.search(line)
            if not annotation_match:
                continue

            tags: list[str] = []
            if groups_match := _JAVA_GROUPS_PATTERN.search(annotation_match.group(0)):
                tags = [
                    g.strip().strip("\"'") for g in groups_match.group(1).split(",") if g.strip()
                ]

            method_name = None
            for lookahead in lines[index : index + 4]:
                if method_match := _JAVA_METHOD_PATTERN.search(lookahead):
                    method_name = method_match.group(1)
                    break
            if method_name is None:
                continue

            identifier = (
                f"{relative}::{current_class}::{method_name}"
                if current_class
                else f"{relative}::{method_name}"
            )
            found.append(
                Test(
                    identifier=identifier,
                    source_file=relative,
                    name=method_name,
                    class_name=current_class,
                    technology=technology,
                    tags=tags,
                    category=classify_test(tags, text),
                )
            )
        return found


# ---------------------------------------------------------------------------
# Python (pytest)
# ---------------------------------------------------------------------------

_PYTHON_CLASS_PATTERN = re.compile(r"^class\s+(Test\w+)")
_PYTHON_TEST_FUNCTION_PATTERN = re.compile(r"^(\s*)def\s+(test_\w+)\s*\(")
_PYTEST_MARK_PATTERN = re.compile(r"@pytest\.mark\.(\w+)")


class PytestTestExtractor:
    technology = "pytest"

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]:
        tests: list[Test] = []
        for path, text in file_contents.items():
            if (
                path.suffix != ".py"
                or "test_" not in path.name
                and not path.name.endswith("_test.py")
            ):
                continue
            if (
                "import pytest" not in text
                and "pytest.mark" not in text
                and "pytest.fixture" not in text
            ):
                continue
            tests.extend(self._extract_from_file(root, path, text))
        return tests

    @staticmethod
    def _extract_from_file(root: Path, path: Path, text: str) -> list[Test]:
        relative = str(path.relative_to(root))
        lines = text.splitlines()
        current_class: str | None = None
        current_class_indent = -1
        found: list[Test] = []

        for index, line in enumerate(lines):
            if class_match := _PYTHON_CLASS_PATTERN.match(line):
                current_class = class_match.group(1)
                current_class_indent = len(line) - len(line.lstrip())
                continue

            function_match = _PYTHON_TEST_FUNCTION_PATTERN.match(line)
            if not function_match:
                continue

            indent = len(function_match.group(1))
            class_name = (
                current_class if current_class and indent > current_class_indent >= 0 else None
            )
            name = function_match.group(2)

            tags = []
            for lookback in reversed(lines[max(0, index - 5) : index]):
                if mark_match := _PYTEST_MARK_PATTERN.match(lookback.strip()):
                    tags.append(mark_match.group(1))
                elif lookback.strip() and not lookback.strip().startswith("@"):
                    break
            tags.reverse()

            identifier = (
                f"{relative}::{class_name}::{name}" if class_name else f"{relative}::{name}"
            )
            found.append(
                Test(
                    identifier=identifier,
                    source_file=relative,
                    name=name,
                    class_name=class_name,
                    technology="pytest",
                    tags=tags,
                    category=classify_test(tags, text),
                )
            )
        return found


# ---------------------------------------------------------------------------
# TypeScript/JavaScript (Playwright)
# ---------------------------------------------------------------------------

_PLAYWRIGHT_DESCRIBE_PATTERN = re.compile(r"test\.describe\(\s*['\"]([^'\"]+)['\"]")
_PLAYWRIGHT_TEST_PATTERN = re.compile(r"\btest\(\s*['\"]([^'\"]+)['\"]")
_PLAYWRIGHT_TAG_PATTERN = re.compile(r"tag:\s*(?:\[([^\]]*)\]|['\"]([^'\"]*)['\"])")


class PlaywrightTestExtractor:
    technology = "Playwright"

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]:
        tests: list[Test] = []
        for path, text in file_contents.items():
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            if "@playwright/test" not in text and "from playwright" not in text.lower():
                continue
            tests.extend(self._extract_from_file(root, path, text))
        return tests

    @staticmethod
    def _extract_from_file(root: Path, path: Path, text: str) -> list[Test]:
        relative = str(path.relative_to(root))
        lines = text.splitlines()
        current_describe: str | None = None
        found: list[Test] = []

        for index, line in enumerate(lines):
            if describe_match := _PLAYWRIGHT_DESCRIBE_PATTERN.search(line):
                current_describe = describe_match.group(1)
            test_match = _PLAYWRIGHT_TEST_PATTERN.search(line)
            if not test_match:
                continue

            name = test_match.group(1)
            tags: list[str] = []
            for lookahead in lines[index : index + 2]:
                if tag_match := _PLAYWRIGHT_TAG_PATTERN.search(lookahead):
                    raw = tag_match.group(1) or tag_match.group(2) or ""
                    tags = [t.strip().strip("\"'").lstrip("@") for t in raw.split(",") if t.strip()]
                    break

            identifier = (
                f"{relative}::{current_describe}::{name}"
                if current_describe
                else f"{relative}::{name}"
            )
            found.append(
                Test(
                    identifier=identifier,
                    source_file=relative,
                    name=name,
                    class_name=current_describe,
                    technology="Playwright",
                    tags=tags,
                    category=classify_test(tags, text),
                )
            )
        return found


# ---------------------------------------------------------------------------
# Cypress — no first-class tagging mechanism without a third-party plugin
# this analyzer can't reliably detect, so `tags` stays empty rather than
# guessed.
# ---------------------------------------------------------------------------

_CYPRESS_DESCRIBE_PATTERN = re.compile(r"describe\(\s*['\"]([^'\"]+)['\"]")
_CYPRESS_IT_PATTERN = re.compile(r"\bit\(\s*['\"]([^'\"]+)['\"]")


class CypressTestExtractor:
    technology = "Cypress"

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]:
        tests: list[Test] = []
        for path, text in file_contents.items():
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            lowered = text.lower()
            if "cypress" not in lowered and "cy.visit(" not in lowered and "cy.get(" not in lowered:
                continue
            tests.extend(self._extract_from_file(root, path, text))
        return tests

    @staticmethod
    def _extract_from_file(root: Path, path: Path, text: str) -> list[Test]:
        relative = str(path.relative_to(root))
        lines = text.splitlines()
        current_describe: str | None = None
        found: list[Test] = []

        for line in lines:
            if describe_match := _CYPRESS_DESCRIBE_PATTERN.search(line):
                current_describe = describe_match.group(1)
            it_match = _CYPRESS_IT_PATTERN.search(line)
            if not it_match:
                continue

            name = it_match.group(1)
            identifier = (
                f"{relative}::{current_describe}::{name}"
                if current_describe
                else f"{relative}::{name}"
            )
            found.append(
                Test(
                    identifier=identifier,
                    source_file=relative,
                    name=name,
                    class_name=current_describe,
                    technology="Cypress",
                    tags=[],
                    category=classify_test([], text),
                )
            )
        return found


# ---------------------------------------------------------------------------
# Robot Framework — delegates the per-test parsing to
# `framework.sync.robot_analysis` (already the canonical Robot text
# parser; kept there rather than duplicated here).
# ---------------------------------------------------------------------------


class RobotTestExtractor:
    technology = "Robot Framework"

    def extract(self, root: Path, file_contents: dict[Path, str]) -> list[Test]:
        tests: list[Test] = []
        for path, text in file_contents.items():
            if path.suffix != ".robot":
                continue
            relative = str(path.relative_to(root))
            for name, tags in extract_robot_tests(text):
                tests.append(
                    Test(
                        identifier=f"{relative}::{name}",
                        source_file=relative,
                        name=name,
                        class_name=None,
                        technology="Robot Framework",
                        tags=tags,
                        category=classify_test(tags, text),
                    )
                )
        return tests


DEFAULT_TEST_EXTRACTORS: list[TestExtractor] = [
    JavaAnnotationTestExtractor(),
    PytestTestExtractor(),
    PlaywrightTestExtractor(),
    CypressTestExtractor(),
    RobotTestExtractor(),
]


def extract_tests(
    root: Path,
    file_contents: dict[Path, str],
    extractors: list[TestExtractor] | None = None,
) -> list[Test]:
    tests: list[Test] = []
    for extractor in extractors if extractors is not None else DEFAULT_TEST_EXTRACTORS:
        tests.extend(extractor.extract(root, file_contents))
    return tests


# ---------------------------------------------------------------------------
# AutomationInventory — the "what do you already have?" aggregate. Every
# count below is either derived directly from already-extracted `Test`
# entries or from the same lightweight token/filename-hint scanning the
# rest of `framework.sync` already uses — never fabricated from file
# presence alone.
# ---------------------------------------------------------------------------

_COMPONENT_HINTS = ("Component.", "component_", "Widget.", "widget_")
_API_CLIENT_TOKENS = (
    "apiclient",
    "requests.session",
    "httpx.client",
    "restassured",
    "requestslibrary",
)
_DATABASE_UTILITY_TOKENS = (
    "queryexecutor",
    "databasemanager",
    "sqlalchemy",
    "connection.cursor",
    "jdbc",
)
_TEST_DATA_DIR_NAMES = ("testdata", "test_data", "fixtures", "data")
_TEST_DATA_EXTENSIONS = (".json", ".csv", ".xlsx", ".yaml", ".yml")
_AUTH_MECHANISM_TOKENS: dict[str, str] = {
    "oauth": "OAuth",
    "bearer": "Bearer Token",
    "basic auth": "Basic Auth",
    "api key": "API Key",
    "apikey": "API Key",
    "jwt": "JWT",
    "session cookie": "Session Cookie",
}
_CI_PIPELINE_HINTS: tuple[tuple[str, str], ...] = (
    ("Jenkinsfile", "Jenkins"),
    (".gitlab-ci.yml", "GitLab CI"),
    ("azure-pipelines.yml", "Azure Pipelines"),
)


def _count_files_matching(file_contents: dict[Path, str], tokens: tuple[str, ...]) -> int:
    return sum(1 for text in file_contents.values() if any(t in text.lower() for t in tokens))


def _count_components(file_contents: dict[Path, str]) -> int:
    return sum(1 for path in file_contents if any(hint in path.name for hint in _COMPONENT_HINTS))


def _count_fixtures(file_contents: dict[Path, str]) -> int:
    return sum(text.count("@pytest.fixture") for text in file_contents.values())


def _count_test_data_sources(root: Path, file_contents: dict[Path, str]) -> int:
    count = 0
    for path in file_contents:
        if path.suffix not in _TEST_DATA_EXTENSIONS:
            continue
        relative_parts = {part.lower() for part in path.relative_to(root).parts[:-1]}
        if relative_parts & set(_TEST_DATA_DIR_NAMES):
            count += 1
    return count


def _authentication_mechanisms(file_contents: dict[Path, str]) -> list[str]:
    found: list[str] = []
    combined_lower = " ".join(file_contents.values()).lower()
    for token, label in _AUTH_MECHANISM_TOKENS.items():
        if token in combined_lower and label not in found:
            found.append(label)
    return found


def _ci_pipeline(root: Path, file_contents: dict[Path, str]) -> str | None:
    for path in file_contents:
        relative = str(path.relative_to(root)).replace("\\", "/")
        if ".github/workflows/" in relative:
            return "GitHub Actions"
    for path in file_contents:
        for filename, label in _CI_PIPELINE_HINTS:
            if path.name == filename:
                return label
    return None


def build_inventory(
    root: Path,
    file_contents: dict[Path, str],
    tests: list[Test],
    robot_structure: RobotStructure | None,
    page_object_like_files: int,
    config_files: int,
) -> AutomationInventory:
    """Aggregates already-extracted `tests` plus lightweight file-level
    scans into the "EXISTING AUTOMATION INVENTORY" summary — see
    docs/FrameworkSync.md.
    """
    class_keys = {(t.source_file, t.class_name) for t in tests if t.class_name}
    tags = sorted({tag for t in tests for tag in t.tags})

    suite_files = {t.source_file for t in tests if t.technology == "Robot Framework"}
    suite_files |= {str(p.relative_to(root)) for p in file_contents if p.name == "testng.xml"}

    return AutomationInventory(
        tests_detected=len(tests),
        test_classes=len(class_keys),
        test_suites=len(suite_files),
        tags=tags,
        page_objects=page_object_like_files,
        components=_count_components(file_contents),
        reusable_keywords=robot_structure.keyword_count if robot_structure else 0,
        fixtures=_count_fixtures(file_contents),
        api_clients=_count_files_matching(file_contents, _API_CLIENT_TOKENS),
        database_utilities=_count_files_matching(file_contents, _DATABASE_UTILITY_TOKENS),
        test_data_sources=_count_test_data_sources(root, file_contents),
        configuration_files=config_files,
        authentication_mechanisms=_authentication_mechanisms(file_contents),
        ci_pipeline=_ci_pipeline(root, file_contents),
        reporting=detect_reporting_tools(file_contents),
    )


def format_inventory(
    inventory: AutomationInventory,
    *,
    language: str,
    ui_framework: str | None,
    runner: str | None,
    primary_execution: str | None,
    parallelism: int | None,
) -> str:
    """Renders the "EXISTING AUTOMATION INVENTORY" block — the first
    thing a customer sees, before any migration talk. Shared by
    `python -m framework.sync analyze`'s console output and the migration
    worksheet, so the two never drift apart.
    """
    rows: list[tuple[str, str | int | None]] = [
        ("Framework", ui_framework),
        ("Test Runner", runner),
        ("Tests Detected", inventory.tests_detected),
        ("Test Classes", inventory.test_classes or None),
        ("Test Suites", inventory.test_suites or None),
        ("Tags/Groups", ", ".join(inventory.tags) or None),
        ("Page Objects", inventory.page_objects or None),
        ("Components", inventory.components or None),
        ("Reusable Keywords", inventory.reusable_keywords or None),
        ("Fixtures", inventory.fixtures or None),
        ("API Clients", inventory.api_clients or None),
        ("Database Utilities", inventory.database_utilities or None),
        ("Test Data Sources", inventory.test_data_sources or None),
        ("Configuration Files", inventory.configuration_files or None),
        ("Authentication", ", ".join(inventory.authentication_mechanisms) or None),
        ("CI Pipeline", inventory.ci_pipeline),
        ("Reporting", ", ".join(inventory.reporting) or None),
        ("Parallelism", parallelism),
    ]

    lines = ["EXISTING AUTOMATION INVENTORY", "", f"Language:              {language}"]
    for label, value in rows:
        if value is None:
            continue
        lines.append(f"{label + ':':23s}{value}")
    if primary_execution:
        lines.append("Primary Execution:")
        lines.append(f"    {primary_execution}")
    return "\n".join(lines)
