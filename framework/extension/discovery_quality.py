"""Discovery quality scoring — the honesty check between "discovery ran
without crashing" and "discovery actually found the customer's
application." A discovery run that only ever reached a login page (the
validated bug: a redirect silently treated as successful discovery of the
target page) must score as `BLOCKED`, not as a normal low score buried in
a report nobody reads before scaffolding.

Every point lost is recorded in `DiscoveryQualityScore.reasons` — see
that model's docstring. This module never claims a score it can't
justify with a concrete signal from the actual discovery data.
"""

from __future__ import annotations

from framework.discovery.models import DiscoveredPage
from framework.extension.auth_detection import detect_login_pages
from framework.extension.models import (
    DiscoveryQualityLevel,
    DiscoveryQualityScore,
    NetworkClassificationResult,
)

_SCORE_HIGH_CONFIDENCE = 70
_SCORE_PARTIAL = 40
_SCORE_LOW_CONFIDENCE = 1


def _level_for_score(score: int) -> DiscoveryQualityLevel:
    if score >= _SCORE_HIGH_CONFIDENCE:
        return DiscoveryQualityLevel.HIGH_CONFIDENCE
    if score >= _SCORE_PARTIAL:
        return DiscoveryQualityLevel.PARTIAL
    if score >= _SCORE_LOW_CONFIDENCE:
        return DiscoveryQualityLevel.LOW_CONFIDENCE
    return DiscoveryQualityLevel.BLOCKED


def compute_discovery_quality(
    pages: list[DiscoveredPage],
    *,
    requested_url: str | None = None,
    classification: NetworkClassificationResult | None = None,
) -> DiscoveryQualityScore:
    """`pages` is the full set of discovered pages (e.g. a `crawl()`
    result); `requested_url`, when given, is treated as the entry point
    the caller actually asked to discover — `pages[0]` is assumed to be
    that entry point (the same assumption `UIDiscoveryEngine.crawl`'s
    breadth-first order already guarantees). `classification`, when
    given, lets a discovery run with zero real application API traffic
    be penalized even when every page looks legitimate on its own.
    """
    if not pages:
        return DiscoveryQualityScore(
            score=0,
            level=DiscoveryQualityLevel.BLOCKED,
            reasons=["No pages were discovered."],
        )

    reasons: list[str] = []
    score = 100
    login_signals = detect_login_pages(pages)
    login_count = sum(1 for signal in login_signals if signal.is_likely_login_page)

    entry_point_is_login = requested_url is not None and login_signals[0].is_likely_login_page
    if entry_point_is_login:
        score -= 70
        entry_evidence = (
            login_signals[0].evidence[0] if login_signals[0].evidence else "no further evidence"
        )
        reasons.append(
            "The requested page appears to be a login page — discovery likely followed "
            f"an authentication redirect instead of reaching the actual target page "
            f"({entry_evidence})."
        )

    login_ratio = login_count / len(pages)
    if login_ratio > 0.5 and not entry_point_is_login:
        score -= 35
        reasons.append(f"{login_count} of {len(pages)} discovered pages appear to be login pages.")

    elements_total = sum(len(page.elements) for page in pages)
    if elements_total == 0:
        score -= 40
        reasons.append("No interactive elements were discovered on any page.")

    if classification is not None:
        if classification.summary.application_candidate_count == 0:
            score -= 30
            reasons.append(
                "No application API traffic was classified — only static/framework/"
                "analytics/authentication noise was observed."
            )
        elif classification.summary.raw_count > 0:
            noise = (
                classification.summary.static_or_framework_ignored
                + classification.summary.analytics_ignored
                + classification.summary.third_party_ignored
                + classification.summary.document_ignored
            )
            if noise / classification.summary.raw_count > 0.9:
                score -= 10
                raw_count = classification.summary.raw_count
                reasons.append(
                    f"Over 90% of raw network calls ({noise} of {raw_count}) were "
                    "static/framework/analytics/third-party noise."
                )

    score = max(0, min(100, score))
    level = _level_for_score(score)
    if entry_point_is_login:
        level = DiscoveryQualityLevel.BLOCKED
        score = min(score, 15)

    if not reasons:
        reasons.append("No quality issues were detected.")

    return DiscoveryQualityScore(score=score, level=level, reasons=reasons)
