"""`lookup_cross_language_mappings` must only ever return entries for
technologies/structural elements actually present in the analysis —
never a speculative or fabricated mapping for something not detected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.cross_language_mapping import lookup_cross_language_mappings
from framework.sync.models import DetectedFramework, MappingStatus, RepositoryAnalysis, SupportLevel

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_no_detected_frameworks_yields_no_mappings() -> None:
    analysis = RepositoryAnalysis(source="empty")
    assert lookup_cross_language_mappings(analysis) == []


def test_detected_selenium_yields_a_playwright_mapping() -> None:
    analysis = RepositoryAnalysis(
        source="test",
        detected_frameworks=[
            DetectedFramework(
                name="Selenium",
                category="ui_automation",
                support_level=SupportLevel.PARTIALLY_SUPPORTED,
            )
        ],
    )

    mappings = lookup_cross_language_mappings(analysis)

    assert len(mappings) == 1
    assert mappings[0].source_technology == "Selenium"
    assert mappings[0].target_technology == "Playwright Page/Locator"
    assert mappings[0].status == MappingStatus.CONCEPTUALLY_MAPPABLE
    assert mappings[0].manual_action  # never empty — always a concrete next step


def test_undetected_technology_never_appears() -> None:
    analysis = RepositoryAnalysis(
        source="test",
        detected_frameworks=[
            DetectedFramework(
                name="pytest", category="test_runner", support_level=SupportLevel.SUPPORTED
            )
        ],
    )

    mappings = lookup_cross_language_mappings(analysis)

    # pytest is already this framework's own runner — no mapping table
    # entry exists for it (nothing to migrate), and no other technology's
    # mapping should appear just because *something* was detected.
    assert mappings == []


def test_robot_structural_mappings_only_appear_for_elements_actually_present() -> None:
    root = _FIXTURES / "robot_requests_library"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    mappings = lookup_cross_language_mappings(analysis)
    concepts = {m.concept for m in mappings}

    assert "Test Case" in concepts  # the fixture has one
    assert "Suite Setup" not in concepts  # the fixture has no Suite Setup
    assert "Resource file" not in concepts  # the fixture has no .resource file


def test_robot_selenium_library_fixture_yields_selenium_and_robot_mappings() -> None:
    root = _FIXTURES / "robot_selenium_library"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    mappings = lookup_cross_language_mappings(analysis)
    sources = {m.source_technology for m in mappings}

    assert "Selenium" in sources
    assert "Robot Framework SeleniumLibrary" in sources
    assert "Robot Framework" in sources  # from the structural (Test Case/Keyword/...) mappings
    assert all(m.status == MappingStatus.CONCEPTUALLY_MAPPABLE for m in mappings)
