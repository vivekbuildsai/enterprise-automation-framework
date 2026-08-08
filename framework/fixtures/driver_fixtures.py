from __future__ import annotations

from collections.abc import Generator

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from pluggy import Result

from framework.config import EnvironmentSettings, get_settings
from framework.drivers.browser_factory import BrowserFactory
from framework.drivers.driver_manager import DriverManager
from framework.logger import get_logger

_logger = get_logger("fixtures")


class _BrowserSession:
    """Lazily launches, and self-heals, one `Browser` process shared by
    every test in this pytest-xdist *worker's* session (a `session`-scoped
    fixture is per-worker, not global — each worker still gets its own
    browser, exactly as before; only the per-test relaunch is removed).
    Playwright's `BrowserContext` already gives every test a fully isolated
    cookie jar/storage/cache regardless of whether the underlying browser
    process is shared, so reusing the process only trades away launch time
    (~500ms measured), never test isolation.
    """

    def __init__(self, playwright: Playwright, config: EnvironmentSettings) -> None:
        self._playwright = playwright
        self._config = config
        self._browser: Browser | None = None

    def get(self) -> Browser:
        if self._browser is None or not self._browser.is_connected():
            if self._browser is not None:
                _logger.warning("Shared browser was disconnected; relaunching for this test.")
            self._browser = BrowserFactory.launch(self._playwright, self._config.browser)
        return self._browser

    def close(self) -> None:
        if self._browser is not None and self._browser.is_connected():
            self._browser.close()


@pytest.fixture(scope="session")
def _browser_session(settings: EnvironmentSettings) -> Generator[_BrowserSession, None, None]:
    playwright = sync_playwright().start()
    session = _BrowserSession(playwright, settings)
    yield session
    session.close()
    playwright.stop()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, Result[pytest.TestReport], None]:
    """Stash each phase's outcome on the test item so the `page` fixture's
    teardown can know whether the test actually failed (fixtures only see
    `call` outcome once the test body has already finished, hence the stash).
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def test_failed(request: pytest.FixtureRequest) -> bool:
    """Whether `request`'s test body actually failed, per the outcome stashed
    by `pytest_runtest_makereport` above. Shared by every fixture that owns a
    `DriverManager` (see also `framework.fixtures.auth_fixtures`) so failure
    detection stays in one place.
    """
    call_report = getattr(request.node, "rep_call", None)
    return bool(call_report and call_report.failed)


@pytest.fixture(scope="session")
def settings() -> EnvironmentSettings:
    return get_settings()


@pytest.fixture
def page(
    request: pytest.FixtureRequest,
    settings: EnvironmentSettings,
    _browser_session: _BrowserSession,
) -> Generator[Page, None, None]:
    """Function-scoped Playwright Page on a worker-shared `Browser` process
    (see `_browser_session`) — each test still gets its own isolated
    `BrowserContext`/`Page` (parallel-safe under `pytest-xdist -n auto`,
    zero state leaks between tests), and artifacts (screenshot/trace/video)
    are only persisted when the test fails.
    """
    manager = DriverManager(
        config=settings.browser, test_name=request.node.nodeid, browser=_browser_session.get()
    )
    driver_page = manager.start()

    yield driver_page

    manager.finalize(test_failed=test_failed(request))


@pytest.fixture
def base_url(settings: EnvironmentSettings) -> str:
    return str(settings.ui.base_url)
