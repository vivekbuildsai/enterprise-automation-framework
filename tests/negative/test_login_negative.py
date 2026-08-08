import allure
import pytest

from framework.assertions import UIAssert
from framework.config import EnvironmentSettings
from framework.pages import LoginPage


@allure.feature("Authentication")
@pytest.mark.ui
@pytest.mark.negative
class TestLoginNegative:
    @pytest.mark.parametrize(
        ("username", "password", "expected_message"),
        [
            ("", "", "Your username is invalid!"),
            ("tomsmith", "wrong-password", "Your password is invalid!"),
            ("wrong-user", "SuperSecretPassword!", "Your username is invalid!"),
        ],
        ids=["empty-credentials", "wrong-password", "wrong-username"],
    )
    def test_invalid_login_shows_specific_error(
        self,
        page,
        settings: EnvironmentSettings,
        username: str,
        password: str,
        expected_message: str,
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)

        with allure.step("Open login page"):
            login_page.open()

        with allure.step(f"Submit invalid credentials (username='{username}')"):
            login_page.login(username, password)

        with allure.step(f"Verify error message: '{expected_message}'"):
            assert expected_message in login_page.error_message()
            UIAssert.url(page, "/login", "Stays on login page after failure")
