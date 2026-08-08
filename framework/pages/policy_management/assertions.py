from __future__ import annotations

from framework.assertions import assert_field_equals


class PolicyAssertions:
    @staticmethod
    def status_is(actual_status: str, expected_status: str, policy_name: str = "") -> None:
        assert_field_equals("Policy", "status", actual_status, expected_status, policy_name)
