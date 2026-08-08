from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class BreadcrumbComponent(BaseComponent):
    """Breadcrumb trail (e.g. `Home > Subscribers > Subscriber #12345`)."""

    def __init__(
        self,
        page: Page,
        root_selector: str = "[aria-label='breadcrumb']",
        *,
        item_selector: str = "li",
    ) -> None:
        super().__init__(page, root_selector)
        self._item_selector = item_selector

    def items(self) -> list[str]:
        return self.child(self._item_selector).all_inner_texts()

    def current(self) -> str:
        items = self.items()
        if not items:
            return ""
        return items[-1]

    def click_item(self, label: str) -> None:
        self.child(self._item_selector).get_by_text(label, exact=True).click()
