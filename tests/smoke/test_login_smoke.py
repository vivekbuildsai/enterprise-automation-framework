import allure
import pytest
from playwright.sync_api import Page

from framework.assertions import Assert
from framework.config import EnvironmentSettings
from framework.pages import LoginPage


@allure.feature("Authentication")
@allure.story("Login")
@pytest.mark.smoke
class TestLoginSmoke:
    def test_valid_login_reaches_secure_area(
        self, page: Page, settings: EnvironmentSettings
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)

        with allure.step("Open login page"):
            login_page.open()

        with allure.step("Submit valid credentials"):
            dashboard = login_page.login(settings.ui.login_username, settings.ui.login_password)

        with allure.step("Verify secure area is reached"):
            Assert.is_true(dashboard.is_loaded(), "Secure area heading visible")
            Assert.contains(
                dashboard.flash_message(),
                "You logged into a secure area!",
                "Post-login flash message",
            )

    def test_invalid_login_shows_error(self, page: Page, settings: EnvironmentSettings) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)

        with allure.step("Open login page"):
            login_page.open()

        with allure.step("Submit invalid credentials"):
            login_page.login("invalid_user", "invalid_password")

        with allure.step("Verify error message is shown"):
            Assert.contains(
                login_page.error_message(),
                "Your username is invalid!",
                "Invalid-login flash message",
            )
