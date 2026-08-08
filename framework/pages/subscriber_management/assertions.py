from __future__ import annotations

from framework.exceptions import ValidationError
from framework.logger import get_logger

_logger = get_logger("SubscriberAssertions")


class SubscriberAssertions:
    """Domain-specific assertions for Subscriber Management — thin wrappers
    over plain dict comparisons (the shape `SubscriberManagementPage`
    returns) rather than DOM locators, since by the time a test asserts on
    a subscriber, the data has already been extracted from the page.
    """

    @staticmethod
    def subscriber_found(row: dict[str, str] | None, last_name: str) -> None:
        if row is None:
            message = f"Expected to find a subscriber with last name '{last_name}', found none"
            _logger.error(message)
            raise ValidationError(message)

    @staticmethod
    def subscriber_not_found(row: dict[str, str] | None, last_name: str) -> None:
        if row is not None:
            message = f"Expected no subscriber with last name '{last_name}', but found {row}"
            _logger.error(message)
            raise ValidationError(message)

    @staticmethod
    def field_equals(row: dict[str, str], field: str, expected: str) -> None:
        actual = row.get(field)
        if actual != expected:
            message = f"Subscriber field '{field}': expected '{expected}', got '{actual}'"
            _logger.error(message)
            raise ValidationError(message)
