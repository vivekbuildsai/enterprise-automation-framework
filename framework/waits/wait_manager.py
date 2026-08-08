from __future__ import annotations

import re
from collections.abc import Callable, Generator
from contextlib import contextmanager

from playwright.sync_api import Locator, Page, Response
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from framework.constants import Timeouts
from framework.exceptions import ElementNotFoundError
from framework.logger import get_logger

_logger = get_logger("WaitManager")

_DOM_STABILITY_OBSERVER_JS = """
() => {
    if (window.__ntrLastMutation === undefined) {
        window.__ntrLastMutation = Date.now();
        new MutationObserver(() => { window.__ntrLastMutation = Date.now(); })
            .observe(document.documentElement, {
                childList: true, subtree: true, attributes: true, characterData: true,
            });
    }
}
"""


class WaitManager:
    """The one place every non-trivial wait condition is implemented. Page
    Objects and Components delegate here (or to the `BasePage` wrappers that
    call this) instead of ever writing `page.wait_for_timeout(...)` — a
    fixed sleep is banned throughout this framework because it's either too
    short (flaky) or too long (slow) for every environment/network
    condition simultaneously, where an explicit condition is neither.
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    # -- Element state -----------------------------------------------------
    def for_visible(
        self, locator: Locator, *, timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS
    ) -> Locator:
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Element never became visible within {timeout_ms}ms"
            ) from exc
        return locator

    def for_hidden(
        self, locator: Locator, *, timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS
    ) -> None:
        try:
            locator.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Element never became hidden within {timeout_ms}ms"
            ) from exc

    def for_attached(
        self, locator: Locator, *, timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS
    ) -> Locator:
        locator.wait_for(state="attached", timeout=timeout_ms)
        return locator

    def for_detached(
        self, locator: Locator, *, timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS
    ) -> None:
        locator.wait_for(state="detached", timeout=timeout_ms)

    # -- Network -------------------------------------------------------
    def for_network_idle(self, *, timeout_ms: int = Timeouts.LONG_WAIT_MS) -> None:
        """Waits until there have been no network connections for 500ms.
        Use sparingly — prefer `expect_api_response` for a specific request;
        network-idle can wait unnecessarily long on pages with polling/analytics.
        """
        self.page.wait_for_load_state("networkidle", timeout=timeout_ms)

    def for_dom_content_loaded(
        self, *, timeout_ms: int = Timeouts.DEFAULT_NAVIGATION_TIMEOUT_MS
    ) -> None:
        self.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)

    @contextmanager
    def expect_api_response(
        self,
        url_pattern: str | re.Pattern[str] | Callable[[Response], bool],
        *,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> Generator[Callable[[], Response], None, None]:
        """Wrap the action that triggers a request, and get back the matched
        response — the reliable way to wait for "the API call this button
        click kicks off has finished", instead of guessing at a sleep:

            with wait_manager.expect_api_response("**/api/subscribers*") as get_response:
                search_button.click()
            response = get_response()
        """
        with self.page.expect_response(url_pattern, timeout=timeout_ms) as response_info:
            yield lambda: response_info.value

    # -- Application chrome ----------------------------------------------
    def for_loader_gone(
        self, loader_locator: Locator, *, timeout_ms: int = Timeouts.LONG_WAIT_MS
    ) -> None:
        """Waits for a loading spinner/overlay to disappear. Tolerates the
        loader never having appeared at all (a fast response can beat the
        first visibility check), which a plain `for_hidden` would not.
        """
        try:
            loader_locator.wait_for(state="visible", timeout=Timeouts.SHORT_WAIT_MS)
        except PlaywrightTimeoutError:
            return  # loader never showed up — nothing to wait out
        self.for_hidden(loader_locator, timeout_ms=timeout_ms)

    def for_toast(
        self,
        toast_locator: Locator,
        *,
        expected_text: str | None = None,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> Locator:
        self.for_visible(toast_locator, timeout_ms=timeout_ms)
        if expected_text is not None:
            toast_locator.get_by_text(expected_text, exact=False).wait_for(
                state="visible", timeout=timeout_ms
            )
        return toast_locator

    def for_dom_stable(
        self,
        *,
        stability_window_ms: int = 300,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> None:
        """Waits until the DOM has had no mutations for `stability_window_ms`
        — useful after an action that triggers async re-renders with no
        single element/network call to key off of (e.g. a client-side sort
        or a multi-step animation settling).
        """
        self.page.evaluate(_DOM_STABILITY_OBSERVER_JS)
        self.page.wait_for_function(
            "(windowStabilityMs) => Date.now() - window.__ntrLastMutation > windowStabilityMs",
            arg=stability_window_ms,
            timeout=timeout_ms,
        )

    def until(
        self,
        predicate: Callable[[], bool],
        *,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
        poll_interval_ms: int = 100,
        description: str = "condition",
    ) -> None:
        """Escape hatch for a bespoke condition Playwright's own locator
        waits don't cover — bounded-poll a Python predicate. The poll
        interval is an implementation detail of *this utility*, not a
        hardcoded wait in test code: callers pass a real condition
        (`description` names it for the timeout error), not a duration.
        """
        elapsed_ms = 0
        while elapsed_ms < timeout_ms:
            if predicate():
                return
            self.page.wait_for_timeout(poll_interval_ms)
            elapsed_ms += poll_interval_ms
        raise ElementNotFoundError(f"Timed out after {timeout_ms}ms waiting for: {description}")
