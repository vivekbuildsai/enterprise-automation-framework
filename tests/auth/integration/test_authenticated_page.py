from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from framework.assertions import Assert
from framework.config import EnvironmentSettings
from framework.pages import DashboardPage

pytestmark = [pytest.mark.auth, pytest.mark.integration]


@allure.feature("Authentication")
@allure.story("Session Reuse")
class TestAuthenticatedPageFixture:
    def test_starts_already_in_the_secure_area_without_submitting_login_form(
        self, authenticated_page: Page, settings: EnvironmentSettings
    ) -> None:
        dashboard = DashboardPage(authenticated_page)
        dashboard.base_url = str(settings.ui.base_url)

        with allure.step("Navigate straight to the secure area using reused session state"):
            dashboard.open()

        with allure.step("Verify the session was already authenticated"):
            Assert.is_true(
                dashboard.is_loaded(),
                "Secure area reached via reused `.auth/user.json` storage state, "
                "with no login form ever submitted by this test",
            )
