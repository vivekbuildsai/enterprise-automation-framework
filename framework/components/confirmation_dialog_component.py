from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class ConfirmationDialogComponent(BaseComponent):
    """A modal specialized for yes/no confirmation ("Delete this policy?").
    Kept separate from `ModalComponent` rather than subclassing it — a
    confirmation dialog's contract is "confirm or cancel", not "primary or
    secondary action", and conflating the two names invites confusion about
    which button does what in a destructive-action flow.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "[data-testid='confirmation-dialog']",
        *,
        message_selector: str = "[data-testid='confirmation-message']",
        confirm_selector: str = "[data-testid='confirmation-confirm']",
        cancel_selector: str = "[data-testid='confirmation-cancel']",
    ) -> None:
        super().__init__(page, root_selector)
        self._message_selector = message_selector
        self._confirm_selector = confirm_selector
        self._cancel_selector = cancel_selector

    def message(self) -> str:
        return self.get_text(self._message_selector, description="Confirmation message")

    def confirm(self) -> None:
        self._logger.debug("Confirming dialog")
        self.click(self._confirm_selector, description="Confirm button")
        self.waits.for_hidden(self.root)

    def cancel(self) -> None:
        self._logger.debug("Cancelling dialog")
        self.click(self._cancel_selector, description="Cancel button")
        self.waits.for_hidden(self.root)
