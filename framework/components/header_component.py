from __future__ import annotations

from playwright.sync_api import Page

from framework.components.base_component import BaseComponent


class HeaderComponent(BaseComponent):
    """Application header/topbar — logo, user menu, global actions
    (notifications bell, settings). Selectors are constructor parameters
    (with conventional defaults) rather than hardcoded, since header markup
    varies by app and this component has no single real target application
    instance to hardcode against yet.
    """

    def __init__(
        self,
        page: Page,
        root_selector: str = "header",
        *,
        user_menu_selector: str = "[data-testid='user-menu']",
        notifications_selector: str = "[data-testid='notifications-bell']",
        logout_selector: str = "[data-testid='logout-button']",
    ) -> None:
        super().__init__(page, root_selector)
        self._user_menu_selector = user_menu_selector
        self._notifications_selector = notifications_selector
        self._logout_selector = logout_selector

    def open_user_menu(self) -> None:
        self.click(self._user_menu_selector, description="User menu")

    def logged_in_user_name(self) -> str:
        return self.get_text(self._user_menu_selector, description="User menu label")

    def click_notifications(self) -> None:
        self.click(self._notifications_selector, description="Notifications bell")

    def logout(self) -> None:
        self.open_user_menu()
        self.click(self._logout_selector, description="Logout")
