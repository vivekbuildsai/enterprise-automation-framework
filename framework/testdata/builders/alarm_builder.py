from __future__ import annotations

from datetime import UTC, datetime

from framework.database.models import Alarm
from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.utilities.id_sequence import sequences

_alarm_sequence = sequences.get("alarm")

_SEVERITIES = ("CRITICAL", "MAJOR", "MINOR", "WARNING")


class AlarmBuilder(BaseBuilder[Alarm]):
    """Fluent builder for `framework.database.models.Alarm`."""

    def with_alarm_id(self, alarm_id: str) -> AlarmBuilder:
        return self._set(alarm_id=alarm_id)

    def with_alarm_code(self, alarm_code: str) -> AlarmBuilder:
        return self._set(alarm_code=alarm_code)

    def with_severity(self, severity: str) -> AlarmBuilder:
        return self._set(severity=severity)

    def with_entity(self, entity_type: str, entity_id: str) -> AlarmBuilder:
        return self._set(entity_type=entity_type, entity_id=entity_id)

    def with_status(self, status: str) -> AlarmBuilder:
        return self._set(status=status)

    def with_description(self, description: str) -> AlarmBuilder:
        return self._set(description=description)

    def critical(self) -> AlarmBuilder:
        return self.with_severity("CRITICAL")

    def active(self) -> AlarmBuilder:
        return self.with_status("ACTIVE")

    def cleared(self, *, cleared_at: str | None = None) -> AlarmBuilder:
        return self._set(status="CLEARED", cleared_at=cleared_at or datetime.now(UTC).isoformat())

    def build(self) -> Alarm:
        return Alarm(
            alarm_id=self._get("alarm_id", lambda: _alarm_sequence.next_id(prefix="ALARM")),
            alarm_code=self._get("alarm_code", lambda: "GEN-001"),
            severity=self._get("severity", lambda: _SEVERITIES[0]),
            entity_type=self._get("entity_type", lambda: "STEERING_ZONE"),
            entity_id=self._get("entity_id", lambda: "ZONE-1"),
            status=self._get("status", lambda: "ACTIVE"),
            raised_at=self._get("raised_at", lambda: datetime.now(UTC).isoformat()),
            cleared_at=self._get("cleared_at", lambda: None),
            description=self._get("description", lambda: "Automatically generated test alarm"),
        )
