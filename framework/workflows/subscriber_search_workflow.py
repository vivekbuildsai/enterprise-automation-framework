from __future__ import annotations

from playwright.sync_api import Page

from framework.pages.subscriber_management import SubscriberManagementPage


class SubscriberSearchWorkflow:
    """Composes navigation + search into one call, matching the shape of
    `LoginWorkflow` — open the module, search, return the result.
    """

    def __init__(self, page: Page, *, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def execute(self, last_name: str) -> dict[str, str] | None:
        subscriber_page = SubscriberManagementPage(self.page)
        subscriber_page.base_url = self.base_url
        subscriber_page.open()
        return subscriber_page.search_subscriber(last_name)
