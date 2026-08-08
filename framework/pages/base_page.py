from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Download, FrameLocator, Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from framework.constants import Timeouts
from framework.exceptions import ElementNotFoundError, ElementNotInteractableError
from framework.locators import Locators
from framework.logger import get_logger
from framework.waits import WaitManager


class BasePage:
    """Base class for every Page Object. Wraps raw Playwright calls with
    framework-level logging and exception translation so page classes stay
    declarative and tests never touch Playwright's API directly (Facade
    Pattern over Playwright).
    """

    base_url: str = ""
    path: str = ""
    # Overridable per Page Object — the common convention for where a toast/
    # notification renders. `click_and_wait_for_toast()` uses this so pages
    # that follow the convention don't each need their own toast constant.
    TOAST_SELECTOR: str = "[data-testid='notification']"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.waits = WaitManager(page)
        self._logger = get_logger(type(self).__name__)

    # -- Navigation ----------------------------------------------------
    def open(self) -> None:
        url = f"{self.base_url.rstrip('/')}/{self.path.lstrip('/')}" if self.path else self.base_url
        self._logger.info(f"Navigating to {url}")
        self.page.goto(url)

    def title(self) -> str:
        return self.page.title()

    def current_url(self) -> str:
        return self.page.url

    def locator(self, selector: str) -> Locator:
        """Raw `Locator` escape hatch — for handing off to `UIAssert` or a
        `BaseComponent` that needs to scope its own lookups under this
        element, without every Page Object reaching into `self.page` directly.
        """
        return self.page.locator(selector)

    # -- Semantic (role/text/title) locators -----------------------------
    # Thin wrappers over `Locators` (framework.locators) — the framework's
    # one designated place for *how* a locator gets built — so a Page
    # Object never has to import `Locators` itself for the common case.
    # Each returns a plain `Locator`, so `.filter()`/`.first`/`.nth()`
    # compose normally; `click_locator()`/`fill_locator()`/`uncheck_locator()`
    # below then interact with it through the same logging/exception-
    # translation every CSS-selector method above already gets.
    def role_locator(self, role: str, *, name: str | None = None, exact: bool = False) -> Locator:
        return Locators.role(self.page, role, name=name, exact=exact)

    def text_locator(self, text: str, *, exact: bool = False) -> Locator:
        return Locators.text(self.page, text, exact=exact)

    def title_locator(self, title: str, *, exact: bool = False) -> Locator:
        return Locators.title(self.page, title, exact=exact)

    def link_with_text_locator(self, text: str, *, exact: bool = False) -> Locator:
        return Locators.link_with_text(self.page, text, exact=exact)

    def click_locator(self, target: Locator, *, description: str = "") -> None:
        label = description or str(target)
        self._logger.debug(f"Clicking '{label}'")
        try:
            target.click()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not find/click '{label}'") from exc

    def fill_locator(self, target: Locator, text: str, *, description: str = "") -> None:
        label = description or str(target)
        self._logger.debug(f"Filling '{label}' with {len(text)} chars")
        try:
            target.fill(text)
        except PlaywrightTimeoutError as exc:
            raise ElementNotInteractableError(f"Could not fill '{label}'") from exc

    def uncheck_locator(self, target: Locator, *, description: str = "") -> None:
        label = description or str(target)
        self._logger.debug(f"Unchecking '{label}'")
        try:
            target.uncheck()
        except PlaywrightTimeoutError as exc:
            raise ElementNotInteractableError(f"Could not uncheck '{label}'") from exc

    def check_locator(self, target: Locator, *, description: str = "") -> None:
        label = description or str(target)
        self._logger.debug(f"Checking '{label}'")
        try:
            target.check()
        except PlaywrightTimeoutError as exc:
            raise ElementNotInteractableError(f"Could not check '{label}'") from exc

    def wait_for_locator_visible(
        self, target: Locator, *, description: str = "", timeout_ms: int | None = None
    ) -> Locator:
        label = description or str(target)
        try:
            target.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"'{label}' never became visible") from exc
        return target

    # -- Resilient element interactions ---------------------------------
    def click(self, selector: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Clicking '{label}'")
        try:
            self.page.locator(selector).click()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not find/click '{label}' ({selector})") from exc

    def double_click(self, selector: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Double-clicking '{label}'")
        try:
            self.page.locator(selector).dblclick()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not double-click '{label}' ({selector})") from exc

    def right_click(self, selector: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Right-clicking '{label}'")
        try:
            self.page.locator(selector).click(button="right")
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not right-click '{label}' ({selector})") from exc

    def hover(self, selector: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Hovering '{label}'")
        try:
            self.page.locator(selector).hover()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not hover '{label}' ({selector})") from exc

    def drag_and_drop(
        self, source_selector: str, target_selector: str, *, description: str = ""
    ) -> None:
        label = description or f"{source_selector} -> {target_selector}"
        self._logger.debug(f"Dragging '{label}'")
        try:
            self.page.locator(source_selector).drag_to(self.page.locator(target_selector))
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not drag-and-drop '{label}'") from exc

    def fill(self, selector: str, text: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Filling '{label}' with {len(text)} chars")
        try:
            self.page.locator(selector).fill(text)
        except PlaywrightTimeoutError as exc:
            raise ElementNotInteractableError(f"Could not fill '{label}' ({selector})") from exc

    def type_text(
        self, selector: str, text: str, *, delay_ms: float = 0, description: str = ""
    ) -> None:
        """Types character-by-character (dispatching real key events), unlike
        `fill()` which sets the value directly — use this when the app reacts
        to keystrokes (autocomplete, input masks, debounced search).
        """
        label = description or selector
        self._logger.debug(f"Typing into '{label}' ({len(text)} chars, delay={delay_ms}ms)")
        try:
            self.page.locator(selector).press_sequentially(text, delay=delay_ms)
        except PlaywrightTimeoutError as exc:
            raise ElementNotInteractableError(
                f"Could not type into '{label}' ({selector})"
            ) from exc

    def press_key(self, key: str, *, selector: str | None = None, description: str = "") -> None:
        """Presses a keyboard key (e.g. `"Enter"`, `"Escape"`, `"Control+A"`)
        either globally or scoped to `selector` if given.
        """
        label = description or selector or "page"
        self._logger.debug(f"Pressing '{key}' on '{label}'")
        if selector is not None:
            self.page.locator(selector).press(key)
        else:
            self.page.keyboard.press(key)

    def mouse_click_at(self, x: float, y: float) -> None:
        self._logger.debug(f"Mouse click at ({x}, {y})")
        self.page.mouse.click(x, y)

    def mouse_move_to(self, x: float, y: float) -> None:
        self._logger.debug(f"Mouse move to ({x}, {y})")
        self.page.mouse.move(x, y)

    def get_text(self, selector: str, *, description: str = "") -> str:
        label = description or selector
        try:
            return self.page.locator(selector).inner_text()
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not read text of '{label}' ({selector})") from exc

    def get_attribute(self, selector: str, name: str, *, description: str = "") -> str | None:
        label = description or selector
        try:
            return self.page.locator(selector).get_attribute(name)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"Could not read attribute '{name}' of '{label}'") from exc

    def is_visible(self, selector: str, *, timeout_ms: int = Timeouts.SHORT_WAIT_MS) -> bool:
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def is_enabled(self, selector: str) -> bool:
        return self.page.locator(selector).is_enabled()

    def is_checked(self, selector: str) -> bool:
        return self.page.locator(selector).is_checked()

    def wait_for_visible(self, selector: str, *, timeout_ms: int | None = None) -> Locator:
        locator = self.page.locator(selector)
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(f"'{selector}' never became visible") from exc
        return locator

    def wait_for_hidden(self, selector: str, *, timeout_ms: int | None = None) -> None:
        self.waits.for_hidden(
            self.page.locator(selector), timeout_ms=timeout_ms or Timeouts.DEFAULT_ACTION_TIMEOUT_MS
        )

    def wait_for_network_idle(self, *, timeout_ms: int = Timeouts.LONG_WAIT_MS) -> None:
        self.waits.for_network_idle(timeout_ms=timeout_ms)

    def wait_for_loader_gone(
        self, loader_selector: str, *, timeout_ms: int = Timeouts.LONG_WAIT_MS
    ) -> None:
        self.waits.for_loader_gone(self.page.locator(loader_selector), timeout_ms=timeout_ms)

    def wait_for_toast(
        self,
        toast_selector: str,
        *,
        expected_text: str | None = None,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> Locator:
        return self.waits.for_toast(
            self.page.locator(toast_selector), expected_text=expected_text, timeout_ms=timeout_ms
        )

    def click_and_wait_for_toast(
        self,
        selector: str,
        *,
        toast_selector: str | None = None,
        expected_text: str | None = None,
        description: str = "",
    ) -> Locator:
        """Clicks `selector` and waits for the resulting toast/notification —
        the "submit an action, confirm it succeeded" pattern that repeats
        across most create/update/delete flows. `toast_selector` defaults to
        `self.TOAST_SELECTOR`; override per-call for a page with more than
        one notification region.
        """
        self.click(selector, description=description)
        return self.wait_for_toast(
            toast_selector or self.TOAST_SELECTOR, expected_text=expected_text
        )

    def wait_for_dom_stable(
        self, *, stability_window_ms: int = 300, timeout_ms: int | None = None
    ) -> None:
        self.waits.for_dom_stable(
            stability_window_ms=stability_window_ms,
            timeout_ms=timeout_ms or Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
        )

    def select_option(self, selector: str, value: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Selecting '{value}' in '{label}'")
        self.page.locator(selector).select_option(value)

    def upload_file(self, selector: str, file_path: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Uploading '{file_path}' to '{label}'")
        self.page.locator(selector).set_input_files(file_path)

    @contextmanager
    def expect_download(
        self, *, timeout_ms: int = Timeouts.LONG_WAIT_MS
    ) -> Generator[Callable[[], Download], None, None]:
        """Wrap the action that triggers a download:

        with page.expect_download() as get_download:
            page.click("#export-button")
        download = get_download()
        download.save_as("/tmp/export.csv")
        """
        with self.page.expect_download(timeout=timeout_ms) as download_info:
            yield lambda: download_info.value

    def download_file(
        self, trigger_selector: str, save_path: str, *, description: str = ""
    ) -> Path:
        """Convenience over `expect_download()` for the common case: click
        something that starts a download, save it, return the saved path.
        """
        label = description or trigger_selector
        self._logger.debug(f"Downloading via '{label}'")
        with self.expect_download() as get_download:
            self.page.locator(trigger_selector).click()
        download = get_download()
        download.save_as(save_path)
        return Path(save_path)

    def accept_alert(self) -> None:
        self.page.once("dialog", lambda dialog: dialog.accept())

    def dismiss_alert(self) -> None:
        self.page.once("dialog", lambda dialog: dialog.dismiss())

    def frame(self, selector: str) -> FrameLocator:
        return self.page.frame_locator(selector)

    # -- Tabs / windows ---------------------------------------------------
    @contextmanager
    def expect_new_tab(
        self, *, timeout_ms: int = Timeouts.DEFAULT_NAVIGATION_TIMEOUT_MS
    ) -> Generator[Callable[[], Page], None, None]:
        """Wrap the action that opens a new tab/window:

        with base_page.expect_new_tab() as get_tab:
            page.click("a[target=_blank]")
        new_tab = get_tab()
        """
        with self.page.context.expect_page(timeout=timeout_ms) as new_page_info:
            yield lambda: new_page_info.value

    def switch_to_window(self, index: int) -> Page:
        """Returns an already-open tab/window by its index in the shared
        browser context (0 = first opened). For a *new* tab triggered by an
        action, prefer `expect_new_tab()` — it's race-free.
        """
        pages = self.page.context.pages
        if index >= len(pages):
            raise ElementNotFoundError(f"No window at index {index}; only {len(pages)} open")
        return pages[index]

    # -- Scrolling ----------------------------------------------------
    def scroll_into_view(self, selector: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Scrolling '{label}' into view")
        self.page.locator(selector).scroll_into_view_if_needed()

    def scroll_to_top(self) -> None:
        self.page.evaluate("() => window.scrollTo(0, 0)")

    def scroll_to_bottom(self) -> None:
        self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")

    # -- Debugging ----------------------------------------------------
    def highlight(self, selector: str, *, color: str = "red", duration_ms: int = 2000) -> None:
        """Draws a temporary colored outline around an element — a debugging
        aid for local runs/screen recordings, not an assertion. No-op risk:
        purely cosmetic, never throws if the element is missing.
        """
        self.page.locator(selector).evaluate(
            """(el, args) => {
                const original = el.style.outline;
                el.style.outline = `3px solid ${args.color}`;
                setTimeout(() => { el.style.outline = original; }, args.durationMs);
            }""",
            {"color": color, "durationMs": duration_ms},
        )

    def screenshot(self, path: str) -> None:
        self.page.screenshot(path=path, full_page=True)

    def element_screenshot(self, selector: str, path: str, *, description: str = "") -> None:
        label = description or selector
        self._logger.debug(f"Screenshotting '{label}'")
        self.page.locator(selector).screenshot(path=path)
