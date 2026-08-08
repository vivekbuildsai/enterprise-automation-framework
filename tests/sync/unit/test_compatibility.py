from __future__ import annotations

import pytest

from framework.sync import (
    DetectedFramework,
    RepositoryAnalysis,
    SupportLevel,
    compute_compatibility_report,
)

pytestmark = pytest.mark.sync


def _analysis(*levels: SupportLevel) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        source="test",
        detected_frameworks=[
            DetectedFramework(name=f"tech-{i}", category="test", support_level=level)
            for i, level in enumerate(levels)
        ],
    )


def test_ratio_is_supported_over_total() -> None:
    analysis = _analysis(
        SupportLevel.SUPPORTED, SupportLevel.SUPPORTED, SupportLevel.REQUIRES_MANUAL_REVIEW
    )
    report = compute_compatibility_report(analysis)

    assert report.total_detected == 3
    assert report.supported_count == 2
    assert report.compatibility_ratio == pytest.approx(2 / 3)


def test_empty_detection_yields_zero_ratio_and_explicit_summary() -> None:
    analysis = _analysis()
    report = compute_compatibility_report(analysis)

    assert report.total_detected == 0
    assert report.compatibility_ratio == 0.0
    assert "manual review" in report.summary.lower()


def test_all_supported_yields_ratio_of_one() -> None:
    analysis = _analysis(SupportLevel.SUPPORTED, SupportLevel.SUPPORTED)
    report = compute_compatibility_report(analysis)
    assert report.compatibility_ratio == 1.0
