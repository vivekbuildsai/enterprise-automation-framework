"""Example A — UI Automation.

Demonstrates: Playwright (via the framework's `page` fixture/`DriverManager`),
Page Objects (`LoginPage`, `DashboardPage`, `SubscriberManagementPage`), a
Component (`TableComponent`, used internally by `SubscriberManagementPage`),
the `Assert` facade, and Allure reporting (`@allure.feature`/`allure.step`).

Runs against the framework's public sample target
(the-internet.herokuapp.com) — no customer application involved.

Run:
    poetry run pytest examples/ui_automation -v --alluredir=reports/allure-results
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page

from framework.assertions import Assert
from framework.config import EnvironmentSettings
from framework.pages import LoginPage
from framework.pages.subscriber_management.page import SubscriberManagementPage


@allure.feature("Example: UI Automation")
@allure.story("Login, then read a data table via a Page Object + Component")
def test_login_then_reads_a_data_table(page: Page, settings: EnvironmentSettings) -> None:
    login_page = LoginPage(page)
    login_page.base_url = str(settings.ui.base_url)

    with allure.step("Open the login page and sign in"):
        login_page.open()
        dashboard = login_page.login(settings.ui.login_username, settings.ui.login_password)

    with allure.step("Verify the secure area was reached"):
        Assert.is_true(dashboard.is_loaded(), "Secure area heading visible")

    with allure.step("Navigate to the sample data table"):
        subscribers = SubscriberManagementPage(page)
        subscribers.base_url = str(settings.ui.base_url)
        subscribers.open()

    with allure.step("Read the table via the Page Object (TableComponent underneath)"):
        row_count = subscribers.subscriber_count()
        first_row = subscribers.search_subscriber("Smith")

    with allure.step("Assert on what the Page Object + Component returned"):
        Assert.is_true(row_count > 0, "the demo table should have at least one row")
        Assert.is_true(first_row is not None, "a row for 'Smith' should exist in the demo table")
