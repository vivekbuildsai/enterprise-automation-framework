"""Sample fixture data for Example C — a small legacy test file."""

from ..login_page import LoginPage


def test_login(driver):
    page = LoginPage(driver)
    page.login("demo_user", "demo_password")
