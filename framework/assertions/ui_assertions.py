from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from framework.constants import Timeouts
from framework.exceptions import ValidationError
from framework.logger import get_logger

_logger = get_logger("UIAssert")


class UIAssert:
    """UI-layer counterpart to `Assert` (which operates on plain Python
    values) — every method here operates on a live Playwright `Locator`/
    `Page`, waits for the relevant state itself (never assumes the element
    is already settled), and raises `ValidationError` with a message naming
    what was expected vs. actually found. Static methods, called directly
    from Page Objects/tests: `UIAssert.contains_text(locator, "Active")`.
    """

    # -- Presence / state -------------------------------------------------
    @staticmethod
    def visible(
        locator: Locator,
        description: str = "",
        *,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> None:
        label = description or "Element"
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ValidationError(
                f"{label}: expected visible, was not within {timeout_ms}ms"
            ) from exc

    @staticmethod
    def hidden(
        locator: Locator,
        description: str = "",
        *,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> None:
        label = description or "Element"
        try:
            locator.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ValidationError(
                f"{label}: expected hidden, was not within {timeout_ms}ms"
            ) from exc

    @staticmethod
    def enabled(locator: Locator, description: str = "") -> None:
        label = description or "Element"
        if not locator.is_enabled():
            raise ValidationError(f"{label}: expected enabled, was disabled")

    @staticmethod
    def disabled(locator: Locator, description: str = "") -> None:
        label = description or "Element"
        if locator.is_enabled():
            raise ValidationError(f"{label}: expected disabled, was enabled")

    # -- Text ---------------------------------------------------------
    @staticmethod
    def contains_text(locator: Locator, expected_substring: str, description: str = "") -> None:
        label = description or "Element"
        actual = locator.inner_text()
        if expected_substring not in actual:
            raise ValidationError(
                f"{label}: expected text to contain '{expected_substring}', got '{actual}'"
            )

    @staticmethod
    def exact_text(locator: Locator, expected_text: str, description: str = "") -> None:
        label = description or "Element"
        actual = locator.inner_text()
        if actual != expected_text:
            raise ValidationError(f"{label}: expected exact text '{expected_text}', got '{actual}'")

    # -- Attributes / CSS ---------------------------------------------
    @staticmethod
    def attribute(locator: Locator, name: str, expected_value: str, description: str = "") -> None:
        label = description or "Element"
        actual = locator.get_attribute(name)
        if actual != expected_value:
            raise ValidationError(
                f"{label}: expected attribute '{name}' to be '{expected_value}', got '{actual}'"
            )

    @staticmethod
    def css(
        locator: Locator, property_name: str, expected_value: str, description: str = ""
    ) -> None:
        label = description or "Element"
        actual = locator.evaluate(
            "(el, prop) => getComputedStyle(el).getPropertyValue(prop)", property_name
        )
        if actual != expected_value:
            raise ValidationError(
                f"{label}: expected CSS '{property_name}' to be '{expected_value}', got '{actual}'"
            )

    # -- Page-level ------------------------------------------------------
    @staticmethod
    def url(page: Page, expected: str, description: str = "", *, exact: bool = False) -> None:
        label = description or "URL"
        actual = page.url
        matched = actual == expected if exact else expected in actual
        if not matched:
            comparison = "equal to" if exact else "containing"
            raise ValidationError(
                f"{label}: expected URL {comparison} '{expected}', got '{actual}'"
            )

    @staticmethod
    def title(page: Page, expected: str, description: str = "", *, exact: bool = False) -> None:
        label = description or "Title"
        actual = page.title()
        matched = actual == expected if exact else expected in actual
        if not matched:
            comparison = "equal to" if exact else "containing"
            raise ValidationError(
                f"{label}: expected title {comparison} '{expected}', got '{actual}'"
            )

    # -- Downloads / toasts --------------------------------------------
    @staticmethod
    def download_success(file_path: str | Path, description: str = "") -> None:
        label = description or "Download"
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"{label}: expected file to exist at '{path}', it does not")
        if path.stat().st_size == 0:
            raise ValidationError(f"{label}: file at '{path}' exists but is empty")

    @staticmethod
    def toast_success(
        locator: Locator,
        expected_text: str | None = None,
        description: str = "",
        *,
        timeout_ms: int = Timeouts.DEFAULT_ACTION_TIMEOUT_MS,
    ) -> None:
        label = description or "Toast"
        UIAssert.visible(locator, label, timeout_ms=timeout_ms)
        if expected_text is not None:
            UIAssert.contains_text(locator, expected_text, label)

    # -- Tables -------------------------------------------------------
    @staticmethod
    def table_data(
        actual_rows: list[list[str]], expected_rows: list[list[str]], description: str = ""
    ) -> None:
        """Compares extracted table data (e.g. from `TableComponent.rows()`)
        against expected rows — kept as a plain data comparison rather than
        DOM-aware so it works with any component's extraction, not just one
        table implementation.
        """
        label = description or "Table data"
        if actual_rows != expected_rows:
            raise ValidationError(f"{label}: expected rows {expected_rows}, got {actual_rows}")
