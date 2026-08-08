from __future__ import annotations

from typing import TYPE_CHECKING

from framework.pages.base_page import BasePage

if TYPE_CHECKING:
    from framework.pages.login_page import LoginPage


class DashboardPage(BasePage):
    """Landing page shown immediately after a successful login (the
    "secure area" in the demo target). Stands in for a real application's
    dashboard/landing page in this sample slice.
    """

    path = "/secure"

    HEADING = "h2"
    FLASH_MESSAGE = "#flash"
    LOGOUT_BUTTON = "a.button"

    def is_loaded(self) -> bool:
        return self.is_visible(self.HEADING) and "Secure Area" in self.get_text(self.HEADING)

    def flash_message(self) -> str:
        return self.get_text(self.FLASH_MESSAGE, description="Flash message").strip()

    def logout(self) -> LoginPage:
        from framework.pages.login_page import LoginPage

        self.click(self.LOGOUT_BUTTON, description="Logout button")
        return LoginPage(self.page)
