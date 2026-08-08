from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page

from framework.auth import AuthStateManager
from framework.config import EnvironmentSettings
from framework.drivers.driver_manager import DriverManager
from framework.exceptions import ConfigurationError
from framework.fixtures.driver_fixtures import _BrowserSession, test_failed
from framework.pages.login_page import LoginPage


@pytest.fixture(scope="session")
def auth_state_manager(settings: EnvironmentSettings) -> AuthStateManager:
    return AuthStateManager(
        state_dir=settings.auth.state_dir,
        max_age_seconds=settings.auth.max_age_seconds,
    )


@pytest.fixture(scope="session")
def auth_state_path(
    settings: EnvironmentSettings,
    auth_state_manager: AuthStateManager,
    _browser_session: _BrowserSession,
) -> Path:
    """Session-scoped: ensure `.auth/{profile}.json` exists and is fresh,
    regenerating it via one throwaway login when missing or expired
    (`AuthStateManager.load_or_create`). Reused by every test in the run
    that asks for `authenticated_page`, so login happens at most once per
    session instead of once per test.

    Requires `auth.enabled: true` for the active environment (see
    `config/environments/*.yaml`) — an explicit per-environment opt-in,
    matching the existing `feature_flags` pattern, since not every target
    application supports/permits storage-state reuse.

    Uses the same shared `_browser_session` as `page`/`authenticated_page`
    rather than starting its own `sync_playwright()` instance — Playwright's
    sync API only supports one active driver connection per thread, so a
    second, independent `sync_playwright()` call started while this worker's
    session-scoped one is still running raises "Sync API inside the asyncio
    loop" — this isn't a style preference, it's a correctness requirement.
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

    return auth_state_manager.load_or_create(
        profile=settings.auth.profile, browser=_browser_session.get(), login=_login
    )


@pytest.fixture
def authenticated_page(
    request: pytest.FixtureRequest,
    settings: EnvironmentSettings,
    auth_state_path: Path,
    _browser_session: _BrowserSession,
) -> Generator[Page, None, None]:
    """Function-scoped Playwright Page, pre-authenticated via the shared
    `.auth/{profile}.json` session state — skips the login form entirely.
    Same per-test isolation and failure-only artifact capture as `page`
    (and the same worker-shared browser process — see `_browser_session`);
    use this instead of `page` for tests that only need to exercise
    already-logged-in behavior.
    """
    manager = DriverManager(
        config=settings.browser,
        test_name=request.node.nodeid,
        storage_state=auth_state_path,
        browser=_browser_session.get(),
    )
    driver_page = manager.start()

    yield driver_page

    manager.finalize(test_failed=test_failed(request))
