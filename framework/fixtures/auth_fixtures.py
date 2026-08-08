from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page, sync_playwright

from framework.auth import AuthStateManager
from framework.config import EnvironmentSettings
from framework.drivers.browser_factory import BrowserFactory
from framework.drivers.driver_manager import DriverManager
from framework.exceptions import ConfigurationError
from framework.fixtures.driver_fixtures import test_failed
from framework.pages.login_page import LoginPage


@pytest.fixture(scope="session")
def auth_state_manager(settings: EnvironmentSettings) -> AuthStateManager:
    return AuthStateManager(
        state_dir=settings.auth.state_dir,
        max_age_seconds=settings.auth.max_age_seconds,
    )


@pytest.fixture(scope="session")
def auth_state_path(settings: EnvironmentSettings, auth_state_manager: AuthStateManager) -> Path:
    """Session-scoped: ensure `.auth/{profile}.json` exists and is fresh,
    regenerating it via one throwaway login when missing or expired
    (`AuthStateManager.load_or_create`). Reused by every test in the run
    that asks for `authenticated_page`, so login happens at most once per
    session instead of once per test.

    Requires `auth.enabled: true` for the active environment (see
    `config/environments/*.yaml`) — an explicit per-environment opt-in,
    matching the existing `feature_flags` pattern, since not every target
    application supports/permits storage-state reuse.
    """
    if not settings.auth.enabled:
        raise ConfigurationError(
            f"Authentication state reuse is disabled for '{settings.environment.value}' "
            "(set `auth.enabled: true` in its environment YAML to use `authenticated_page`)."
        )

    def _login(context: BrowserContext) -> None:
        login_page = LoginPage(context.new_page())
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()
        login_page.login(settings.ui.login_username, settings.ui.login_password)

    with sync_playwright() as playwright:
        browser = BrowserFactory.launch(playwright, settings.browser)
        try:
            return auth_state_manager.load_or_create(
                profile=settings.auth.profile, browser=browser, login=_login
            )
        finally:
            browser.close()


@pytest.fixture
def authenticated_page(
    request: pytest.FixtureRequest,
    settings: EnvironmentSettings,
    auth_state_path: Path,
) -> Generator[Page, None, None]:
    """Function-scoped Playwright Page, pre-authenticated via the shared
    `.auth/{profile}.json` session state — skips the login form entirely.
    Same per-test isolation and failure-only artifact capture as `page`;
    use this instead of `page` for tests that only need to exercise
    already-logged-in behavior.
    """
    manager = DriverManager(
        config=settings.browser,
        test_name=request.node.nodeid,
        storage_state=auth_state_path,
    )
    driver_page = manager.start()

    yield driver_page

    manager.finalize(test_failed=test_failed(request))
