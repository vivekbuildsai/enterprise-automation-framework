from __future__ import annotations

from framework.exceptions import ValidationError


def assert_field_equals(
    entity_label: str, field_label: str, actual: str, expected: str, identifier: str = ""
) -> None:
    """Shared implementation behind the module-specific `*_is()` assertions
    (`PolicyAssertions.status_is`, `AlarmAssertions.status_is`,
    `UserManagementAssertions.role_is`, ...) — those keep distinct public
    names because they mean different domain concepts, but were otherwise
    identical modulo which noun appears in the message. One implementation,
    several thin call sites.
    """
    if actual != expected:
        suffix = f" {identifier}" if identifier else ""
        raise ValidationError(
            f"{entity_label}{suffix}: expected {field_label} '{expected}', got '{actual}'"
        )
