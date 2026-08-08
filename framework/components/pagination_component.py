from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class PaginationComponent(BaseComponent):
    """Page-through control for a table/grid — next/previous, jump-to-page,
    and current/total page reporting.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='pagination']",
        *,
        next_selector: str = "[data-testid='pagination-next']",
        previous_selector: str = "[data-testid='pagination-prev']",
        current_page_selector: str = "[data-testid='pagination-current']",
    ) -> None:
        super().__init__(page, root_selector)
        self._next_selector = next_selector
        self._previous_selector = previous_selector
        self._current_page_selector = current_page_selector

    def next_page(self) -> None:
        self.click(self._next_selector, description="Next page")

    def previous_page(self) -> None:
        self.click(self._previous_selector, description="Previous page")

    def go_to_page(self, page_number: int) -> None:
        self.root.get_by_role("button", name=str(page_number), exact=True).click()

    def current_page(self) -> int:
        return int(self.get_text(self._current_page_selector, description="Current page"))

    def is_next_enabled(self) -> bool:
        return self.child(self._next_selector).is_enabled()

    def is_previous_enabled(self) -> bool:
        return self.child(self._previous_selector).is_enabled()
