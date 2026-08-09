"""Login-page detection — the fix for the second half of the validated
bug: a login-page redirect being wrongly treated as successful discovery
of the customer's actual target page.
"""

from __future__ import annotations

import pytest

from framework.discovery.models import DiscoveredElement, DiscoveredLocator, DiscoveredPage
from framework.extension.auth_detection import detect_login_page, detect_login_pages

pytestmark = pytest.mark.extension


def _page(**overrides: object) -> DiscoveredPage:
    defaults: dict[str, object] = {
        "url": "https://app.example.com/dashboard",
        "title": "Dashboard",
        "elements": [],
        "network_calls": [],
    }
    defaults.update(overrides)
    return DiscoveredPage(**defaults)  # type: ignore[arg-type]


def _password_element() -> DiscoveredElement:
    return DiscoveredElement(
        tag="input",
        element_type="textbox",
        locator=DiscoveredLocator(strategy="css", value="input[name='password']"),
        attributes={"type": "password"},
    )


def test_login_url_path_is_detected() -> None:
    page = _page(url="https://app.example.com/c/portal/login", title="Home")

    signal = detect_login_page(page)

    assert signal.is_likely_login_page is True
    assert any("URL path" in reason for reason in signal.evidence)


def test_login_title_is_detected() -> None:
    page = _page(url="https://app.example.com/", title="Please Sign In")

    signal = detect_login_page(page)

    assert signal.is_likely_login_page is True
    assert any("title" in reason for reason in signal.evidence)


def test_password_field_is_detected() -> None:
    page = _page(elements=[_password_element()])

    signal = detect_login_page(page)

    assert signal.is_likely_login_page is True
    assert any("password" in reason for reason in signal.evidence)


def test_ordinary_dashboard_page_is_not_flagged() -> None:
    page = _page()

    signal = detect_login_page(page)

    assert signal.is_likely_login_page is False
    assert signal.evidence == []


def test_multiple_signals_are_all_recorded() -> None:
    page = _page(
        url="https://app.example.com/login",
        title="Sign In",
        elements=[_password_element()],
    )

    signal = detect_login_page(page)

    assert signal.is_likely_login_page is True
    assert len(signal.evidence) == 3


def test_detect_login_pages_preserves_order() -> None:
    pages = [
        _page(url="https://app.example.com/login", title="Sign In"),
        _page(url="https://app.example.com/dashboard", title="Dashboard"),
    ]

    signals = detect_login_pages(pages)

    assert [s.is_likely_login_page for s in signals] == [True, False]
    assert [s.page_url for s in signals] == [p.url for p in pages]
