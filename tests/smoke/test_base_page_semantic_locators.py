from __future__ import annotations

import pytest
from playwright.sync_api import Page

from framework.exceptions import ElementNotFoundError
from framework.pages.base_page import BasePage

pytestmark = pytest.mark.smoke

_HTML = """
<html><body>
  <label for="u">Username</label>
  <input id="u" role="textbox" aria-label="Username" />
  <label for="p">Password</label>
  <input id="p" role="textbox" aria-label="Password" type="password" />
  <button>Sign In</button>
  <a href="#">Reports Generate, export</a>
  <input type="checkbox" checked aria-label="opt" />
  <p>Diagram view</p>
  <a href="#" title="Search">Search 1</a>
  <a href="#" title="Search">Search 2</a>
</body></html>
"""


def test_role_text_title_locators_interact_correctly(page: Page) -> None:
    """Exercises every BasePage semantic-locator method (role/text/title —
    for target applications with no data-testid/CSS hooks to key off, only
    ARIA roles and visible text) against a real, local Playwright page, so
    the plumbing is verified independent of any specific target app.
    """
    page.set_content(_HTML)
    bp = BasePage(page)

    bp.fill_locator(bp.role_locator("textbox", name="Username"), "adm", description="Username")
    assert page.locator("#u").input_value() == "adm"

    bp.click_locator(bp.role_locator("button", name="Sign In"), description="Sign In")
    bp.click_locator(
        bp.role_locator("link", name="Reports Generate, export"), description="Reports link"
    )
    bp.click_locator(bp.text_locator("Diagram view", exact=True), description="Diagram view")

    bp.uncheck_locator(bp.role_locator("checkbox").first, description="checkbox")
    assert not page.locator("input[type=checkbox]").is_checked()

    assert bp.title_locator("Search").count() == 2
    bp.wait_for_locator_visible(bp.title_locator("Search").nth(1), description="2nd Search")


def test_click_locator_raises_framework_exception_for_missing_element(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    page.context.set_default_timeout(500)
    bp = BasePage(page)

    with pytest.raises(ElementNotFoundError):
        bp.click_locator(bp.role_locator("button", name="Does Not Exist"), description="missing")
