from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class GridComponent(BaseComponent):
    """Card/tile-based listing — the alternative to `TableComponent` for
    screens that render results as cards rather than rows (e.g. a
    dashboard's alarm cards, a policy gallery).
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='grid']",
        *,
        item_selector: str = "[data-testid='grid-item']",
    ) -> None:
        super().__init__(page, root_selector)
        self._item_selector = item_selector

    def item_count(self) -> int:
        return self.child(self._item_selector).count()

    def items_text(self) -> list[str]:
        return self.child(self._item_selector).all_inner_texts()

    def click_item_by_index(self, index: int) -> None:
        self.child(self._item_selector).nth(index).click()

    def click_item_by_text(self, text: str) -> None:
        self.child(self._item_selector).filter(has_text=text).first.click()
