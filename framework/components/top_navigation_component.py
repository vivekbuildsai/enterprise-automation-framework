from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.locators import Locators


class TopNavigationComponent(BaseComponent):
    """Horizontal tab/menu navigation (e.g. module switcher tabs at the top
    of the app). Same by-accessible-name lookup convention as `SidebarComponent`.
    """

    def __init__(self, page: Page, root_selector: str = "[data-testid='top-nav']") -> None:
        super().__init__(page, root_selector)

    def click_tab(self, label: str) -> None:
        self._logger.debug(f"Top nav: clicking tab '{label}'")
        Locators.role(self.root, "tab", name=label).click()

    def active_tab(self, *, active_class: str = "active") -> str | None:
        tabs = self.root.get_by_role("tab")
        for i in range(tabs.count()):
            tab = tabs.nth(i)
            classes = tab.get_attribute("class") or ""
            if active_class in classes.split():
                return tab.inner_text()
        return None

    def tabs(self) -> list[str]:
        return self.root.get_by_role("tab").all_inner_texts()
