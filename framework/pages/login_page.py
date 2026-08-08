from __future__ import annotations

from framework.pages.base_page import BasePage
from framework.pages.dashboard_page import DashboardPage


class LoginPage(BasePage):
    path = "/login"

    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"  # nosec B105 - CSS selector, not a credential
    SUBMIT_BUTTON = "button[type='submit']"
    FLASH_MESSAGE = "#flash"

    def login(self, username: str, password: str) -> DashboardPage:
        self.fill(self.USERNAME_INPUT, username, description="Username field")
        self.fill(self.PASSWORD_INPUT, password, description="Password field")
        self.click(self.SUBMIT_BUTTON, description="Login submit button")
        return DashboardPage(self.page)

    def error_message(self) -> str:
        return self.get_text(self.FLASH_MESSAGE, description="Flash message").strip()
