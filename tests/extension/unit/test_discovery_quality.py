"""Discovery quality scoring — validates that a discovery run which only
ever reached a login page is scored `BLOCKED`, not buried as an ordinary
low score, and that every score change traces to a concrete reason.
"""

from __future__ import annotations

import pytest

from framework.discovery.models import DiscoveredElement, DiscoveredLocator, DiscoveredPage
from framework.extension.discovery_quality import compute_discovery_quality
from framework.extension.models import DiscoveryQualityLevel
from framework.extension.network_classification import classify_network_calls
from tests.extension.unit.test_network_classification import _call

pytestmark = pytest.mark.extension


def _element() -> DiscoveredElement:
    return DiscoveredElement(
        tag="button",
        element_type="button",
        locator=DiscoveredLocator(strategy="test_id", value="submit"),
    )


def _page(**overrides: object) -> DiscoveredPage:
    defaults: dict[str, object] = {
        "url": "https://app.example.com/dashboard",
        "title": "Dashboard",
        "elements": [_element()],
        "network_calls": [],
    }
    defaults.update(overrides)
    return DiscoveredPage(**defaults)  # type: ignore[arg-type]


def test_no_pages_is_blocked() -> None:
    score = compute_discovery_quality([])

    assert score.level is DiscoveryQualityLevel.BLOCKED
    assert score.score == 0
    assert score.reasons


def test_healthy_dashboard_with_elements_and_application_traffic_is_high_confidence() -> None:
    page = _page()
    classification = classify_network_calls(
        [_call(path="/api/employees/42", host="app.example.com")],
        page_host="app.example.com",
    )

    score = compute_discovery_quality([page], requested_url=page.url, classification=classification)

    assert score.level is DiscoveryQualityLevel.HIGH_CONFIDENCE
    assert score.score >= 70


def test_requested_entry_point_resolving_to_login_page_is_blocked() -> None:
    login_page = _page(url="https://app.example.com/c/portal/login", title="Sign In", elements=[])

    score = compute_discovery_quality(
        [login_page], requested_url="https://app.example.com/dashboard"
    )

    assert score.level is DiscoveryQualityLevel.BLOCKED
    assert score.score <= 15
    assert any("login page" in reason for reason in score.reasons)


def test_majority_login_pages_without_requested_url_is_penalized() -> None:
    pages = [
        _page(url="https://app.example.com/login", title="Sign In", elements=[]),
        _page(url="https://app.example.com/logout", title="Signed Out", elements=[]),
        _page(),
    ]

    score = compute_discovery_quality(pages)

    assert score.level in (DiscoveryQualityLevel.PARTIAL, DiscoveryQualityLevel.LOW_CONFIDENCE)
    assert any("appear to be login pages" in reason for reason in score.reasons)


def test_no_interactive_elements_is_penalized() -> None:
    page = _page(elements=[])

    score = compute_discovery_quality([page])

    assert any("No interactive elements" in reason for reason in score.reasons)
    assert score.score <= 60


def test_zero_application_candidates_in_classification_is_penalized() -> None:
    page = _page()
    classification = classify_network_calls(
        [_call(path="/images/logo.png")], page_host="app.example.com"
    )

    score = compute_discovery_quality([page], classification=classification)

    assert any("No application API traffic" in reason for reason in score.reasons)


def test_reasons_are_never_empty_even_when_score_is_perfect() -> None:
    page = _page()
    classification = classify_network_calls(
        [_call(path="/api/employees/42", host="app.example.com")],
        page_host="app.example.com",
    )

    score = compute_discovery_quality([page], classification=classification)

    assert score.reasons
