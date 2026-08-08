from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.constants import Timeouts


class ModalComponent(BaseComponent):
    """Generic modal/dialog overlay. Covers the common shape (title, body,
    primary/secondary action, close button) — app-specific modals with
    extra content compose this via a subclass or by using `child()` for the
    bits this base doesn't know about.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[role='dialog']",
        *,
        title_selector: str = "[data-testid='modal-title']",
        body_selector: str = "[data-testid='modal-body']",
        primary_button_selector: str = "[data-testid='modal-primary-button']",
        secondary_button_selector: str = "[data-testid='modal-secondary-button']",
        close_button_selector: str = "[data-testid='modal-close']",
    ) -> None:
        super().__init__(page, root_selector)
        self._title_selector = title_selector
        self._body_selector = body_selector
        self._primary_button_selector = primary_button_selector
        self._secondary_button_selector = secondary_button_selector
        self._close_button_selector = close_button_selector

    def is_open(self, *, timeout_ms: int = Timeouts.SHORT_WAIT_MS) -> bool:
        return self.is_displayed(timeout_ms=timeout_ms)

    def title(self) -> str:
        return self.get_text(self._title_selector, description="Modal title")

    def body_text(self) -> str:
        return self.get_text(self._body_selector, description="Modal body")

    def click_primary(self) -> None:
        self.click(self._primary_button_selector, description="Modal primary button")

    def click_secondary(self) -> None:
        self.click(self._secondary_button_selector, description="Modal secondary button")

    def close(self) -> None:
        self.click(self._close_button_selector, description="Modal close button")
        self.waits.for_hidden(self.root)
