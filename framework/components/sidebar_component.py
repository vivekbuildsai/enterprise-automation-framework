from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.locators import Locators


class SidebarComponent(BaseComponent):
    """Left-hand navigation menu. Items are looked up by their visible
    accessible name (link/button role) rather than a positional CSS
    selector, so re-ordering the menu in the app doesn't break every test
    that navigates through it.
    """

    def __init__(self, page: Page, root_selector: str = "[data-testid='sidebar']") -> None:
        super().__init__(page, root_selector)

    def click_item(self, label: str) -> None:
        self._logger.debug(f"Sidebar: clicking '{label}'")
        Locators.role(self.root, "link", name=label).click()

    def is_item_active(self, label: str, *, active_class: str = "active") -> bool:
        item = Locators.role(self.root, "link", name=label)
        classes = item.get_attribute("class") or ""
        return active_class in classes.split()

    def items(self) -> list[str]:
        return self.root.get_by_role("link").all_inner_texts()

    def toggle_collapse(self, *, toggle_selector: str = "[data-testid='sidebar-toggle']") -> None:
        self.click(toggle_selector, description="Sidebar collapse toggle")
