from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class DropdownComponent(BaseComponent):
    """Supports both a native `<select>` (`native=True`, the default — use
    Playwright's own `select_option`, no click-to-open needed) and a custom
    div-based dropdown (`native=False` — click to open, click an option by
    text), since enterprise apps mix both depending on the widget library.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str,
        *,
        native: bool = True,
        option_selector: str = "[role='option']",
    ) -> None:
        super().__init__(page, root_selector)
        self._native = native
        self._option_selector = option_selector

    def select(self, option_text: str) -> None:
        self._logger.debug(f"Selecting '{option_text}' (native={self._native})")
        if self._native:
            self.root.select_option(label=option_text)
        else:
            self.root.click()
            self.page.locator(self._option_selector).get_by_text(option_text, exact=True).click()

    def selected_value(self) -> str:
        if self._native:
            return self.root.locator("option:checked").inner_text()
        raise NotImplementedError(
            "Reading the selected value of a non-native dropdown depends on how the app "
            "renders it (a label span, an attribute, ...) — override in a subclass for "
            "the specific widget once real markup is available."
        )

    def options(self) -> list[str]:
        if self._native:
            return self.root.locator("option").all_inner_texts()
        self.root.click()
        texts = self.page.locator(self._option_selector).all_inner_texts()
        self.page.keyboard.press("Escape")
        return texts
