from __future__ import annotations

from pydantic import BaseModel


class AlarmData(BaseModel):
    alarm_id: str
    severity: str


class AlarmTestDataBuilder:
    @staticmethod
    def critical_alarm(alarm_id: str) -> AlarmData:
        return AlarmData(alarm_id=alarm_id, severity="Critical")
