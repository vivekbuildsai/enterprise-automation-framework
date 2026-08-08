from __future__ import annotations

from collections.abc import Callable

from framework.logger import get_logger

_logger = get_logger("CleanupRegistry")


class CleanupRegistry:
    """Registers teardown callables and executes them in LIFO order (last
    registered, first torn down — mirrors creation-dependency order: if B
    was created after A because it depended on A, B must be deleted before
    A). Used by pytest fixtures to guarantee "created records get deleted"
    even when a test fails partway through, since fixture teardown runs
    regardless of test outcome.
    """

    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []

    def register(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def execute_all(self) -> list[Exception]:
        """Executes every registered callback in LIFO order, collecting
        (not raising) any exceptions so one failing cleanup doesn't prevent
        the rest from running. Returns whatever exceptions occurred so the
        caller can decide whether to re-raise or just log them.
        """
        errors: list[Exception] = []
        while self._callbacks:
            callback = self._callbacks.pop()
            try:
                callback()
            except Exception as exc:  # noqa: BLE001 - one failure must not block the rest
                _logger.error(f"Cleanup callback failed: {exc}")
                errors.append(exc)
        return errors

    def clear(self) -> None:
        self._callbacks.clear()

    def __len__(self) -> int:
        return len(self._callbacks)
