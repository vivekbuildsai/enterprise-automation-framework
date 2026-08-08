from __future__ import annotations

from framework.assertions import assert_field_equals


class AlarmAssertions:
    @staticmethod
    def status_is(actual_status: str, expected_status: str, alarm_id: str = "") -> None:
        assert_field_equals("Alarm", "status", actual_status, expected_status, alarm_id)
