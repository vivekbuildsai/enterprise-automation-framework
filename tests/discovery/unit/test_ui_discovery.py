from __future__ import annotations

import pytest
from playwright.sync_api import Page

from framework.discovery import UIDiscoveryEngine

pytestmark = pytest.mark.discovery

_HTML = """
<html><body>
  <button data-testid="submit-btn">Submit</button>
  <a href="/reports" aria-label="Open reports">Reports</a>
  <input id="username" name="username" type="text" />
  <select name="country"><option>US</option></select>
  <div>Not interactive, should be ignored</div>
  <button>Cancel</button>
  <input type="text" />
  <label for="password">Password</label>
  <input id="password" type="password" />
</body></html>
"""


def test_discover_page_finds_only_stably_locatable_elements(page: Page) -> None:
    page.set_content(_HTML)

    result = UIDiscoveryEngine(page).discover_page()

    values = {el.locator.value for el in result.elements}
    assert "submit-btn" in values
    assert "link" in values
    assert "#username" in values
    assert 'select[name="country"]' in values


def test_discover_page_uses_visible_text_as_the_accessible_name_for_a_bare_button(
    page: Page,
) -> None:
    """A button with no aria-label still has a real, usable accessible name
    — its own visible text (`get_by_role("button", name="Cancel")` is
    exactly the pattern `framework.locators.Locators.role()` already uses
    elsewhere in this framework) — so it must be discovered, not dropped.
    """
    page.set_content(_HTML)

    result = UIDiscoveryEngine(page).discover_page()

    cancel_button = next(el for el in result.elements if el.text == "Cancel")
    assert cancel_button.locator.strategy == "role"
    assert cancel_button.locator.accessible_name == "Cancel"


def test_discover_page_drops_elements_with_no_stable_locator(page: Page) -> None:
    """An `<input>` with no id/name/aria-label/placeholder and no inner
    text has genuinely nothing stable to key off — it must not appear,
    rather than falling back to a guessed nth-child-style locator.
    """
    page.set_content(_HTML)

    result = UIDiscoveryEngine(page).discover_page()

    assert not any(
        el.tag == "input" and not el.attributes.get("id") and el.locator.value == "input"
        for el in result.elements
    )
    input_locator_values = {el.locator.value for el in result.elements if el.tag == "input"}
    assert input_locator_values == {"#username", "Password"}


def test_discover_page_uses_an_associated_label_over_a_bare_css_id(page: Page) -> None:
    """A `<label for="...">` is a real, human-meaningful locator source
    (`Locators.label()` -> `get_by_label()`), ranked above a bare CSS id
    selector — matches the testid > role > label > css priority.
    """
    page.set_content(_HTML)

    result = UIDiscoveryEngine(page).discover_page()

    password_field = next(el for el in result.elements if el.attributes.get("type") == "password")
    assert password_field.locator.strategy == "label"
    assert password_field.locator.value == "Password"


def test_discover_page_captures_role_and_accessible_name(page: Page) -> None:
    page.set_content(_HTML)

    result = UIDiscoveryEngine(page).discover_page()

    reports_link = next(el for el in result.elements if el.locator.value == "link")
    assert reports_link.locator.accessible_name == "Open reports"


def test_crawl_respects_max_pages_and_same_origin(page: Page) -> None:
    page.route(
        "https://example.test/start",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body='<a href="https://example.test/next">next</a>'
            '<a href="https://other-origin.test/away">away</a>',
        ),
    )
    page.route(
        "https://example.test/next",
        lambda route: route.fulfill(status=200, content_type="text/html", body="<p>done</p>"),
    )

    pages = UIDiscoveryEngine(page).crawl("https://example.test/start", max_pages=5)

    urls = {p.url for p in pages}
    assert "https://example.test/start" in urls
    assert "https://example.test/next" in urls
    assert not any("other-origin" in u for u in urls)
