from __future__ import annotations

from types import TracebackType

from framework.logger import get_logger

_logger = get_logger("SoftAssert")


class SoftAssert:
    """Collects multiple assertion failures within a `with` block instead of
    stopping at the first one — useful for form-validation or dashboard
    checks where you want the full picture of what's wrong in one run.

    Usage:
        with SoftAssert() as soft:
            soft.equals(actual_title, "Dashboard", "page title")
            soft.is_true(page.is_visible(...), "logout button visible")
        # raises AssertionError here if any check failed, listing all of them
    """

    def __init__(self) -> None:
        self._failures: list[str] = []

    def equals(self, actual: object, expected: object, description: str = "") -> None:
        if actual != expected:
            self._record(f"{description or 'value'}: expected '{expected}', got '{actual}'")

    def contains(self, container: object, member: object, description: str = "") -> None:
        if member not in container:  # type: ignore[operator]
            self._record(f"{description or 'value'}: expected '{member}' to be in '{container}'")

    def is_true(self, condition: bool, description: str = "") -> None:
        if not condition:
            self._record(f"{description or 'condition'}: expected True, got False")

    def is_false(self, condition: bool, description: str = "") -> None:
        if condition:
            self._record(f"{description or 'condition'}: expected False, got True")

    def _record(self, message: str) -> None:
        _logger.warning(f"Soft assertion failed: {message}")
        self._failures.append(message)

    def __enter__(self) -> SoftAssert:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            return  # let real exceptions propagate untouched
        if self._failures:
            joined = "\n  - ".join(self._failures)
            raise AssertionError(f"{len(self._failures)} soft assertion(s) failed:\n  - {joined}")
