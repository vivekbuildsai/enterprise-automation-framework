"""A repository combining two languages must never be collapsed into a
single "primary language" result — the fixture is TypeScript-primary
(2 UI test files) with a Python secondary layer (1 API helper file), a
common real-world shape (mostly one language, one supporting language).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_mixed_language_repository_reports_both_languages() -> None:
    root = _FIXTURES / "mixed_language"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    assert analysis.primary_language == "TypeScript"
    assert analysis.language_breakdown["TypeScript"] == 2
    assert analysis.language_breakdown["Python"] == 1
    # Python is a real secondary language here — never silently dropped
    # just because it isn't the primary one.
    assert "Python" in analysis.language_breakdown


def test_mixed_language_repository_still_detects_the_ui_framework() -> None:
    root = _FIXTURES / "mixed_language"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    names = {f.name for f in analysis.detected_frameworks}
    assert "Playwright" in names


def test_worksheet_lists_secondary_languages_explicitly() -> None:
    from framework.sync import generate_migration_worksheet

    root = _FIXTURES / "mixed_language"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))
    worksheet = generate_migration_worksheet(analysis)

    assert "Primary language: **TypeScript**" in worksheet
    assert "Also detected:" in worksheet
    assert "Python (1 files)" in worksheet
