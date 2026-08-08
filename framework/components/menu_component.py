from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.locators import Locators


class MenuComponent(BaseComponent):
    """Persistent navigation menu — items reachable by `role="link"`
    accessible name, scoped under a root container.

    `root_selector` defaults to `body` (unscoped) since a target
    application's real containing element for this menu varies by app —
    pass the real container selector once it's confirmed against a
    specific application, rather than guessing one here.
    """

    def __init__(self, page: Page, root_selector: str = "body") -> None:
        super().__init__(page, root_selector)

    def click_item(self, label: str) -> None:
        self._logger.debug(f"Menu: clicking '{label}'")
        Locators.role(self.root, "link", name=label).click()
