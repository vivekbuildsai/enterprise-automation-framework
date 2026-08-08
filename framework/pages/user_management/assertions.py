from __future__ import annotations

from framework.assertions import assert_field_equals


class UserManagementAssertions:
    @staticmethod
    def role_is(actual_role: str, expected_role: str, username: str = "") -> None:
        assert_field_equals("User", "role", actual_role, expected_role, username)
