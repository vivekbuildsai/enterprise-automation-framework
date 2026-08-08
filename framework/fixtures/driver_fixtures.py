from __future__ import annotations

from collections.abc import Generator

import pytest
from playwright.sync_api import Page
from pluggy import Result

from framework.config import EnvironmentSettings, get_settings
from framework.drivers.driver_manager import DriverManager
from framework.logger import get_logger

_logger = get_logger("fixtures")


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
    request: pytest.FixtureRequest, settings: EnvironmentSettings
) -> Generator[Page, None, None]:
    """Function-scoped Playwright Page. Each test gets its own browser +
    context (parallel-safe under `pytest-xdist -n auto`), and artifacts
    (screenshot/trace/video) are only persisted when the test fails.
    """
    manager = DriverManager(config=settings.browser, test_name=request.node.nodeid)
    driver_page = manager.start()

    yield driver_page

    manager.finalize(test_failed=test_failed(request))


@pytest.fixture
def base_url(settings: EnvironmentSettings) -> str:
    return str(settings.ui.base_url)
