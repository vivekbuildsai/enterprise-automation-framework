from __future__ import annotations

import pytest
from playwright.sync_api import Page

from framework.assertions import Assert, SoftAssert
from framework.config import EnvironmentSettings
from framework.logger import get_logger


class BaseTest:
    """Optional base class for class-style test suites. Injects `self.page`
    and `self.settings` from the standard fixtures via an autouse fixture, so
    test methods can read `self.page` / `self.settings` directly instead of
    declaring them as parameters on every method.

    Function-style tests (`def test_x(page, settings): ...`) work exactly the
    same without inheriting from this class — it's a convenience, not a
    requirement.
    """

    page: Page
    settings: EnvironmentSettings
    assert_that = Assert
    soft_assert = SoftAssert

    @pytest.fixture(autouse=True)
    def _inject_dependencies(self, page: Page, settings: EnvironmentSettings) -> None:
        self.page = page
        self.settings = settings
        self._logger = get_logger(type(self).__name__)
