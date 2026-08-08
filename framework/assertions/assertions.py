from __future__ import annotations

from framework.exceptions import ValidationError
from framework.logger import get_logger

_logger = get_logger("Assert")


class Assert:
    """Hard-assertion facade. Every check logs before raising, so failures
    are traceable in the structured log even outside of pytest's own output,
    and every failure raises the framework's `ValidationError` so callers can
    catch one type regardless of what was being checked (UI, API, or DB).
    """

    @staticmethod
    def equals(actual: object, expected: object, description: str = "") -> None:
        if actual != expected:
            message = f"{description or 'Assertion'} failed: expected '{expected}', got '{actual}'"
            _logger.error(message)
            raise ValidationError(message)
        _logger.debug(f"{description or 'Assertion'} passed: '{actual}' == '{expected}'")

    @staticmethod
    def not_equals(actual: object, expected: object, description: str = "") -> None:
        if actual == expected:
            message = (
                f"{description or 'Assertion'} failed: expected value to differ from '{expected}'"
            )
            _logger.error(message)
            raise ValidationError(message)

    @staticmethod
    def contains(container: object, member: object, description: str = "") -> None:
        if member not in container:  # type: ignore[operator]
            message = f"{description or 'Assertion'} failed: '{member}' not found in '{container}'"
            _logger.error(message)
            raise ValidationError(message)

    @staticmethod
    def is_true(condition: bool, description: str = "") -> None:
        if not condition:
            message = f"{description or 'Assertion'} failed: expected True"
            _logger.error(message)
            raise ValidationError(message)

    @staticmethod
    def is_false(condition: bool, description: str = "") -> None:
        if condition:
            message = f"{description or 'Assertion'} failed: expected False"
            _logger.error(message)
            raise ValidationError(message)
