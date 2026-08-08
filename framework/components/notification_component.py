from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent
from framework.constants import Timeouts


class NotificationComponent(BaseComponent):
    """Toast/snackbar notification. Success/error is read from a CSS class
    on the root by default (the common convention); pass a different
    `variant_attribute`/class scheme via the constructor if the app encodes
    it differently.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='notification']",
        *,
        success_class: str = "success",
        error_class: str = "error",
        dismiss_selector: str = "[data-testid='notification-dismiss']",
    ) -> None:
        super().__init__(page, root_selector)
        self._success_class = success_class
        self._error_class = error_class
        self._dismiss_selector = dismiss_selector

    def wait_and_get_text(self, *, timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS) -> str:
        self.waits.for_visible(self.root, timeout_ms=timeout_ms)
        return self.root.inner_text()

    def is_success(self) -> bool:
        classes = self.root.get_attribute("class") or ""
        return self._success_class in classes.split()

    def is_error(self) -> bool:
        classes = self.root.get_attribute("class") or ""
        return self._error_class in classes.split()

    def dismiss(self) -> None:
        self.click(self._dismiss_selector, description="Dismiss notification")
        self.waits.for_hidden(self.root)
