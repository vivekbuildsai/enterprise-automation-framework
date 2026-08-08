from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class SearchBoxComponent(BaseComponent):
    """Search input + button, with optional autocomplete suggestions list."""

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='search-box']",
        *,
        input_selector: str = "input",
        submit_selector: str = "[data-testid='search-submit']",
        suggestions_selector: str = "[data-testid='search-suggestion']",
    ) -> None:
        super().__init__(page, root_selector)
        self._input_selector = input_selector
        self._submit_selector = submit_selector
        self._suggestions_selector = suggestions_selector

    def search(self, query: str) -> None:
        self._logger.debug(f"Searching for '{query}'")
        self.fill(self._input_selector, query, description="Search input")
        self.click(self._submit_selector, description="Search submit")

    def type_query(self, query: str) -> None:
        """Types (not fills) into the search box — use when suggestions are
        driven by keystroke events rather than a submitted value.
        """
        self.child(self._input_selector).press_sequentially(query)

    def clear(self) -> None:
        self.child(self._input_selector).fill("")

    def suggestions(self) -> list[str]:
        return self.child(self._suggestions_selector).all_inner_texts()

    def select_suggestion(self, text: str) -> None:
        self.child(self._suggestions_selector).get_by_text(text, exact=False).click()
