import pytest
from playwright.sync_api import Page


@pytest.fixture
def base_url() -> str:
    return "https://example.test"


@pytest.mark.smoke
def test_valid_login_reaches_secure_area(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login")
    page.fill("#username", "demo_user")
    page.fill("#password", "demo_password")
    page.click("#login")
    assert page.locator("h2").inner_text() == "Secure Area"


@pytest.mark.regression
def test_invalid_password_shows_error(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login")
    page.fill("#username", "demo_user")
    page.fill("#password", "wrong_password")
    page.click("#login")
    assert page.locator(".error").is_visible()


class TestDashboard:
    @pytest.mark.regression
    def test_dashboard_shows_welcome_message(self, page: Page, base_url: str) -> None:
        page.goto(f"{base_url}/dashboard")
        assert page.locator(".welcome").is_visible()
