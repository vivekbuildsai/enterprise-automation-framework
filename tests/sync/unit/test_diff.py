from __future__ import annotations

import pytest

from framework.sync import (
    DetectedFramework,
    Finding,
    RepositoryAnalysis,
    RepositoryStructure,
    SupportLevel,
    diff_analyses,
)

pytestmark = pytest.mark.sync


def test_detects_new_and_removed_frameworks() -> None:
    before = RepositoryAnalysis(
        source="a",
        detected_frameworks=[
            DetectedFramework(
                name="Selenium", category="ui", support_level=SupportLevel.PARTIALLY_SUPPORTED
            )
        ],
    )
    after = RepositoryAnalysis(
        source="a",
        detected_frameworks=[
            DetectedFramework(
                name="Playwright", category="ui", support_level=SupportLevel.SUPPORTED
            )
        ],
    )

    result = diff_analyses(before, after)

    assert result.new_frameworks == ["Playwright"]
    assert result.removed_frameworks == ["Selenium"]


def test_computes_file_count_delta() -> None:
    before = RepositoryAnalysis(source="a", structure=RepositoryStructure(total_files=10))
    after = RepositoryAnalysis(source="a", structure=RepositoryStructure(total_files=15))

    result = diff_analyses(before, after)
    assert result.file_count_delta == 5


def test_new_and_resolved_findings() -> None:
    before = RepositoryAnalysis(
        source="a",
        findings=[Finding(category="hardcoded_url", file="a.py", line=1, description="old")],
    )
    after = RepositoryAnalysis(
        source="a",
        findings=[Finding(category="hardcoded_url", file="b.py", line=2, description="new")],
    )

    result = diff_analyses(before, after)

    assert len(result.new_findings) == 1
    assert result.new_findings[0].file == "b.py"
    assert result.resolved_findings_count == 1
