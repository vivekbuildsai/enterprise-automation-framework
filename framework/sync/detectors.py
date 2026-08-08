from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from framework.sync.models import DetectedFramework, SupportLevel


class FrameworkAdapter(Protocol):
    """Detects one automation technology's fingerprint in an already-read
    set of file contents and reports a `DetectedFramework` with an
    explicit `support_level` + migration `notes`. Adapters are the
    extension point for "framework mapping" (see docs/FrameworkSync.md)
    — add a new adapter to recognize a new technology, rather than
    hardcoding detection logic into `RepositoryAnalyzer`.
    """

    name: str
    category: str

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None: ...


@lru_cache(maxsize=4096)
def _lower(text: str) -> str:
    """`_matches` is called once per adapter (13 as of this writing) with
    the *same* `file_contents` dict each time, so without caching, every
    file's text gets `.lower()`-ed up to 13x per `analyze()` call —
    measured as a real ~55% slowdown on a 611-file repository once the
    adapter count grew past the original 6 (see docs/FrameworkSync.md
    performance notes). CPython caches a string's hash after first use, so
    repeat lookups for the same (identical, reused) string object are a
    cheap dict hit, not a rehash. Bounded (not unbounded) so a very large
    or long-running batch of `analyze()` calls can't grow this without limit.
    """
    return text.lower()


def _matches(file_contents: dict[Path, str], *patterns: str) -> list[Path]:
    """Case-insensitive substring match. Case-insensitive because the
    *same* token can legitimately appear in different cases across
    ecosystems — e.g. Python/JS import Playwright as lowercase
    `playwright`, while C# uses the `Microsoft.Playwright` NuGet package
    (capital P) and `OpenQA.Selenium` (capital O/S) vs. Java/Python's
    lowercase `org.openqa.selenium`/`selenium`. A case-sensitive check
    would silently miss real evidence in those ecosystems. Purely
    additive relative to case-sensitive matching — never matches less
    than before, only possibly more.
    """
    lowered_patterns = [p.lower() for p in patterns]
    return [
        path
        for path, text in file_contents.items()
        if any(p in _lower(text) for p in lowered_patterns)
    ]


def _matches_pattern(
    file_contents: dict[Path, str], suffixes: tuple[str, ...], pattern: re.Pattern[str]
) -> list[Path]:
    """Regex match, scoped to specific file suffixes — for evidence tokens
    too generic to trust as a bare substring across every file in the
    repository (e.g. Robot Framework's `Browser` library name, or C#'s
    `[Test]` attribute), where the surrounding syntax/file type is part of
    the evidence, not just the token itself.
    """
    return [
        path
        for path, text in file_contents.items()
        if path.suffix in suffixes and pattern.search(text)
    ]


def _relative(root: Path, paths: list[Path], limit: int = 5) -> list[str]:
    return [str(p.relative_to(root)) for p in paths[:limit]]


class PlaywrightAdapter:
    name = "Playwright"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(
            file_contents,
            "playwright",
            "from playwright",
            "@playwright/test",
            'require("playwright")',
        )
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "Already this framework's UI engine — Page Objects can be ported with "
                "minimal changes."
            ),
        )


class SeleniumAdapter:
    name = "Selenium"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(
            file_contents, "selenium", "webdriver", "from selenium", "org.openqa.selenium"
        )
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "Structural concepts map directly (WebDriver.find_element -> Playwright "
                "page.locator, explicit waits -> WaitManager) but locators and waits must be "
                "re-verified against the real application, not mechanically translated."
            ),
        )


class CypressAdapter:
    name = "Cypress"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(file_contents, "cypress", "cy.visit(", "cy.get(")
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "Chained-command style — concepts map to Playwright actions, but this is a "
                "different runtime/language target than this framework's Python core, so it "
                "requires a manual rewrite, not a mechanical port."
            ),
        )


class PytestAdapter:
    name = "pytest"
    category = "test_runner"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(file_contents, "import pytest", "pytest.mark", "pytest.fixture") + [
            path for path in file_contents if path.name in ("pytest.ini", "conftest.py")
        ]
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "Same test runner this framework already uses — tests can be ported without a "
                "runner migration."
            ),
        )


class JUnitAdapter:
    name = "JUnit"
    category = "test_runner"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(file_contents, "org.junit", "@Test", "extends TestCase")
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.REQUIRES_MANUAL_REVIEW,
            evidence=_relative(root, hits),
            notes=(
                "Java test runner — porting to this Python/pytest-based framework requires a "
                "full test rewrite."
            ),
        )


class TestNGAdapter:
    name = "TestNG"
    category = "test_runner"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(file_contents, "org.testng", "@Test(", "testng.xml")
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.REQUIRES_MANUAL_REVIEW,
            evidence=_relative(root, hits),
            notes="Java test runner — same manual-rewrite caveat as JUnit.",
        )


class WebdriverIOAdapter:
    name = "WebdriverIO"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches(file_contents, "@wdio/", "webdriverio", "wdio.conf")
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "WebDriver-protocol-based, TypeScript/JavaScript runtime — concepts map to "
                "Playwright actions, but this is a different language target than this "
                "framework's Python core, so it requires a manual rewrite."
            ),
        )


_NUNIT_PATTERN = re.compile(r"NUnit\.Framework|\[TestFixture\]")


class NUnitAdapter:
    name = "NUnit"
    category = "test_runner"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches_pattern(file_contents, (".cs",), _NUNIT_PATTERN)
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.REQUIRES_MANUAL_REVIEW,
            evidence=_relative(root, hits),
            notes=(
                "C# test runner — porting to this Python/pytest-based framework requires a "
                "full test rewrite."
            ),
        )


_XUNIT_PATTERN = re.compile(r"\bXunit\b|\[Fact\]|\[Theory\]")


class XUnitAdapter:
    name = "xUnit"
    category = "test_runner"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches_pattern(file_contents, (".cs",), _XUNIT_PATTERN)
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.REQUIRES_MANUAL_REVIEW,
            evidence=_relative(root, hits),
            notes="C# test runner — same manual-rewrite caveat as NUnit.",
        )


_ROBOT_SUFFIXES = (".robot", ".resource")


class RobotFrameworkAdapter:
    """Robot Framework is a keyword-driven automation DSL, not "Python" —
    detected by its own `.robot`/`.resource` files existing at all (the
    strongest possible evidence: nothing else produces these extensions),
    with dependency-declaration mentions ("robotframework" in
    requirements.txt/pyproject.toml) as a secondary signal. See
    docs/FrameworkSync.md, "Robot Framework is first-class."
    """

    name = "Robot Framework"
    category = "automation_dsl"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        file_hits = [path for path in file_contents if path.suffix in _ROBOT_SUFFIXES]
        dependency_hits = _matches(file_contents, "robotframework", "robot framework")
        hits = file_hits or dependency_hits
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.REQUIRES_MANUAL_REVIEW,
            evidence=_relative(root, hits),
            notes=(
                "Keyword-driven DSL, not source code in a general-purpose language — Test "
                "Cases/Keywords/Resource files require a full rewrite as Python "
                "tests/Page-Objects/components, though individual keyword *concepts* often map "
                "cleanly (see the library-specific adapters below)."
            ),
        )


_ROBOT_SELENIUM_LIBRARY_PATTERN = re.compile(
    r"^Library\s+SeleniumLibrary\b", re.IGNORECASE | re.MULTILINE
)


class RobotSeleniumLibraryAdapter:
    name = "Robot Framework SeleniumLibrary"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches_pattern(file_contents, _ROBOT_SUFFIXES, _ROBOT_SELENIUM_LIBRARY_PATTERN)
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "WebDriver-based, same tier as this framework's own Selenium adapter — "
                "keyword-level browser interactions (Open Browser, Input Text, Click "
                "Button, ...) conceptually map to Playwright Page/Locator actions, but "
                "locators and waits must be re-verified, not mechanically translated."
            ),
        )


_ROBOT_BROWSER_LIBRARY_PATTERN = re.compile(r"^Library\s+Browser\s*$", re.IGNORECASE | re.MULTILINE)


class RobotBrowserLibraryAdapter:
    name = "Robot Framework Browser Library"
    category = "ui_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches_pattern(file_contents, _ROBOT_SUFFIXES, _ROBOT_BROWSER_LIBRARY_PATTERN)
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "Built on Playwright under the hood — of all Robot UI libraries, this one's "
                "keyword-level browser interactions map most directly onto this framework's "
                "own Playwright-based `BasePage`, though the keyword-to-method rewrite is "
                "still manual."
            ),
        )


_ROBOT_REQUESTS_LIBRARY_PATTERN = re.compile(
    r"^Library\s+RequestsLibrary\b", re.IGNORECASE | re.MULTILINE
)


class RobotRequestsLibraryAdapter:
    name = "Robot Framework RequestsLibrary"
    category = "api_automation"

    def detect(self, root: Path, file_contents: dict[Path, str]) -> DetectedFramework | None:
        hits = _matches_pattern(file_contents, _ROBOT_SUFFIXES, _ROBOT_REQUESTS_LIBRARY_PATTERN)
        if not hits:
            return None
        return DetectedFramework(
            name=self.name,
            category=self.category,
            support_level=SupportLevel.PARTIALLY_SUPPORTED,
            evidence=_relative(root, hits),
            notes=(
                "HTTP API testing keywords (Create Session, GET/POST On Session, ...) map "
                "conceptually onto this framework's `framework.api.ApiClient` — same concept "
                "(HTTP API testing), different client library and language."
            ),
        )


DEFAULT_ADAPTERS: list[FrameworkAdapter] = [
    PlaywrightAdapter(),
    SeleniumAdapter(),
    CypressAdapter(),
    WebdriverIOAdapter(),
    PytestAdapter(),
    JUnitAdapter(),
    TestNGAdapter(),
    NUnitAdapter(),
    XUnitAdapter(),
    RobotFrameworkAdapter(),
    RobotSeleniumLibraryAdapter(),
    RobotBrowserLibraryAdapter(),
    RobotRequestsLibraryAdapter(),
]
