from __future__ import annotations

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


def _matches(file_contents: dict[Path, str], *patterns: str) -> list[Path]:
    return [path for path, text in file_contents.items() if any(p in text for p in patterns)]


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


DEFAULT_ADAPTERS: list[FrameworkAdapter] = [
    PlaywrightAdapter(),
    SeleniumAdapter(),
    CypressAdapter(),
    PytestAdapter(),
    JUnitAdapter(),
    TestNGAdapter(),
]
