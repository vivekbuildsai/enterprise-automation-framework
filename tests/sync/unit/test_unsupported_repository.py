"""Empty / unknown / malformed repositories must produce a useful,
explicit result — never a crash, never a fabricated compatibility score.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer, compute_compatibility_report

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_empty_repository_is_explicitly_unclassified(tmp_path: Path) -> None:
    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert analysis.primary_language == "unknown"
    assert analysis.detected_frameworks == []
    assert analysis.structure.total_files == 0

    report = compute_compatibility_report(analysis)
    assert report.total_detected == 0
    assert report.compatibility_ratio == 0.0
    assert "manual review" in report.summary.lower()


def test_unknown_repository_detects_no_frameworks_without_crashing() -> None:
    root = _FIXTURES / "unknown_repo"
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    assert analysis.detected_frameworks == []
    assert analysis.primary_language == "unknown"  # README.md has no recognized language extension

    report = compute_compatibility_report(analysis)
    assert report.total_detected == 0
    assert "manual review" in report.summary.lower()


def test_malformed_repository_analyzes_without_crashing() -> None:
    """Deliberately unparseable/invalid Java and Robot Framework content —
    `RepositoryAnalyzer` never compiles or executes anything it reads, so
    malformed source must degrade gracefully (partial/imperfect evidence
    is fine; a crash or a fabricated score is not).
    """
    root = _FIXTURES / "malformed_repo"

    analysis = RepositoryAnalyzer().analyze(root, source=str(root))

    assert analysis.structure.total_files == 2
    # Some real evidence is still findable in the garbled text (e.g. a
    # literal "Library    SeleniumLibrary" line) — the point is that
    # nothing crashes and nothing is fabricated beyond what's actually
    # there in the text.
    report = compute_compatibility_report(analysis)
    assert report.total_detected == len(analysis.detected_frameworks)
    assert 0.0 <= report.compatibility_ratio <= 1.0


def test_partially_recognizable_repository_flags_only_what_is_actually_present(
    tmp_path: Path,
) -> None:
    (tmp_path / "notes.md").write_text("# Project notes\nNo automation code yet.\n")
    (tmp_path / "config.yaml").write_text("environment: dev\n")

    analysis = RepositoryAnalyzer().analyze(tmp_path, source=str(tmp_path))

    assert analysis.detected_frameworks == []
    assert analysis.structure.config_files >= 1
    assert analysis.structure.total_files == 2
