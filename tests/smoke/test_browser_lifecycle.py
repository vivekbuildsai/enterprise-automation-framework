"""Regression coverage for the shared-browser-process optimization in
`framework.fixtures.driver_fixtures._BrowserSession` / `DriverManager`.

Two properties must both hold simultaneously, and this file proves each
with real Playwright behavior rather than mocks:

1. The underlying `Browser` *process* is reused across tests within one
   worker (that's the whole point of the optimization).
2. Each test still gets a fully isolated `BrowserContext` — no cookies,
   storage, or navigation state leak from one test into the next.

Execution order matters here (state is compared *across* test functions),
so this relies on pytest's default in-file execution order — these tests
are not marked for parallel/random reordering.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.smoke

_seen_browser_ids: list[int] = []


def test_first_test_records_the_shared_browsers_identity(page: Page) -> None:
    _seen_browser_ids.append(id(page.context.browser))
    assert page.context.browser is not None
    assert page.context.browser.is_connected()


def test_second_test_reuses_the_same_browser_process(page: Page) -> None:
    _seen_browser_ids.append(id(page.context.browser))
    assert len(_seen_browser_ids) == 2
    assert _seen_browser_ids[0] == _seen_browser_ids[1], (
        "expected the same Browser process to be reused across tests within "
        "one worker — the whole point of the shared-browser optimization"
    )


def test_a_cookie_set_in_this_test_does_not_leak_into_the_next(page: Page) -> None:
    page.goto("https://the-internet.herokuapp.com/")
    page.context.add_cookies(
        [
            {
                "name": "leftover_from_previous_test",
                "value": "1",
                "url": "https://the-internet.herokuapp.com",
            }
        ]
    )
    assert page.context.cookies("https://the-internet.herokuapp.com")


def test_a_new_test_starts_with_a_clean_context_despite_the_shared_browser(
    page: Page,
) -> None:
    page.goto("https://the-internet.herokuapp.com/")
    cookie_names = {c["name"] for c in page.context.cookies("https://the-internet.herokuapp.com")}
    assert "leftover_from_previous_test" not in cookie_names, (
        "BrowserContext isolation must hold even though the Browser process "
        "is shared across tests"
    )


def test_shared_browser_self_heals_after_being_closed_out_from_under_it(
    request: pytest.FixtureRequest,
) -> None:
    """Simulates a mid-session browser crash: close the shared browser
    directly, then confirm the *next* `page` fixture invocation notices the
    disconnect and relaunches rather than raising or hanging.
    """
    browser_session = request.getfixturevalue("_browser_session")
    browser_session.get().close()
    assert not browser_session._browser.is_connected()

    recovered = browser_session.get()
    assert recovered.is_connected()


def test_a_fresh_page_fixture_works_normally_after_recovery(page: Page) -> None:
    page.goto("https://the-internet.herokuapp.com/")
    assert "the-internet" in page.url
