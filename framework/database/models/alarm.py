from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Alarm:
    alarm_id: str
    alarm_code: str
    severity: str
    entity_type: str
    entity_id: str
    status: str
    raised_at: str
    cleared_at: str | None
    description: str
