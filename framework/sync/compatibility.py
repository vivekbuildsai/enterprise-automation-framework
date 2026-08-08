from __future__ import annotations

from framework.sync.models import CompatibilityReport, RepositoryAnalysis, SupportLevel


def compute_compatibility_report(analysis: RepositoryAnalysis) -> CompatibilityReport:
    """A transparent, inspectable ratio — never a fabricated score.

    `compatibility_ratio = supported_count / total_detected`, counted
    directly from `analysis.detected_frameworks`' `support_level` values.
    If nothing was detected, the ratio is left at `0.0` with an explicit
    "manual review required" summary rather than an arbitrary default —
    an undetected repository is not "0% compatible" in any meaningful
    sense, it's simply unclassified.
    """
    counts = {level: 0 for level in SupportLevel}
    for framework in analysis.detected_frameworks:
        counts[framework.support_level] += 1

    total = len(analysis.detected_frameworks)
    ratio = counts[SupportLevel.SUPPORTED] / total if total else 0.0

    if total == 0:
        summary = "No known automation/test framework was detected — manual review required."
    else:
        summary = (
            f"{counts[SupportLevel.SUPPORTED]}/{total} detected technologies are fully supported, "
            f"{counts[SupportLevel.PARTIALLY_SUPPORTED]} partially supported, "
            f"{counts[SupportLevel.REQUIRES_MANUAL_REVIEW]} require manual review."
        )

    return CompatibilityReport(
        supported_count=counts[SupportLevel.SUPPORTED],
        partially_supported_count=counts[SupportLevel.PARTIALLY_SUPPORTED],
        manual_review_count=counts[SupportLevel.REQUIRES_MANUAL_REVIEW],
        total_detected=total,
        compatibility_ratio=ratio,
        summary=summary,
    )
