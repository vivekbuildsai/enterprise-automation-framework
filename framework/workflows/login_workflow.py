from __future__ import annotations

from playwright.sync_api import Page

from framework.pages import DashboardPage, LoginPage


class LoginWorkflow:
    """Composes `LoginPage` -> `DashboardPage` into the one call every other
    workflow/test needs to get past authentication. The Workflow Layer
    exists exactly for this: a business-level action ("log in as this
    user") that happens to require driving more than one Page Object,
    without every test re-deriving the sequence.
    """

    def __init__(self, page: Page, *, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def execute(self, username: str, password: str) -> DashboardPage:
        login_page = LoginPage(self.page)
        login_page.base_url = self.base_url
        login_page.open()
        return login_page.login(username, password)
