from __future__ import annotations

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from framework.constants import Timeouts
from framework.exceptions import ElementNotFoundError
from framework.logger import get_logger
from framework.waits import WaitManager


class BaseComponent:
    """Base class for reusable UI widgets (nav bar, data table, modal,
    notification toast) that appear across many pages. A component is scoped
    to a root Locator, so all internal lookups are automatically relative —
    two instances of the same component on one page never collide (Page
    Component Model).
    """

    def __init__(self, page: Page, root_selector: str) -> None:
        self.page = page
        self.root: Locator = page.locator(root_selector)
        self.waits = WaitManager(page)
        self._logger = get_logger(type(self).__name__)

    def is_displayed(self, *, timeout_ms: int = 5_000) -> bool:
        try:
            self.root.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:  # noqa: BLE001
            return False

    def child(self, selector: str) -> Locator:
        return self.root.locator(selector)

    # -- Scoped interactions — same conventions as BasePage, but every
    # lookup is relative to `self.root` so this component never accidentally
    # matches an identical element belonging to a sibling instance.
    def click(self, child_selector: str, *, description: str = "") -> None:
        label = description or child_selector
        self._logger.debug(f"Clicking '{label}'")
        try:
            self.child(child_selector).click()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Could not find/click '{label}' in {type(self).__name__}"
            ) from exc

    def fill(self, child_selector: str, text: str, *, description: str = "") -> None:
        label = description or child_selector
        self._logger.debug(f"Filling '{label}' with {len(text)} chars")
        self.child(child_selector).fill(text)

    def hover(self, child_selector: str, *, description: str = "") -> None:
        label = description or child_selector
        self._logger.debug(f"Hovering '{label}'")
        self.child(child_selector).hover()

    def get_text(self, child_selector: str, *, description: str = "") -> str:
        label = description or child_selector
        try:
            return self.child(child_selector).inner_text()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Could not read text of '{label}' in {type(self).__name__}"
            ) from exc

    def is_visible(self, child_selector: str, *, timeout_ms: int = Timeouts.SHORT_WAIT_MS) -> bool:
        try:
            self.child(child_selector).wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def wait_for_visible(self, child_selector: str, *, timeout_ms: int | None = None) -> Locator:
        return self.waits.for_visible(
            self.child(child_selector), timeout_ms=timeout_ms or Timeouts.DEFAULT_ACTION_TIMEOUT_MS
        )
