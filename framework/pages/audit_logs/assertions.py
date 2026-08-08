from __future__ import annotations

from framework.exceptions import ValidationError


class AuditLogAssertions:
    @staticmethod
    def entry_contains(entries: list[list[str]], expected_substring: str) -> None:
        if not any(expected_substring in cell for row in entries for cell in row):
            raise ValidationError(
                f"Expected an audit log entry containing '{expected_substring}', "
                f"found none in {entries}"
            )

    @staticmethod
    def entry_count(entries: list[list[str]], expected_count: int) -> None:
        if len(entries) != expected_count:
            raise ValidationError(
                f"Expected {expected_count} audit log entries, got {len(entries)}"
            )
