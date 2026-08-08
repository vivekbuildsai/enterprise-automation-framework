from __future__ import annotations

from dataclasses import asdict

from framework.database.models import Alarm
from framework.database.queries import AlarmQueries
from framework.database.repositories.base_repository import BaseRepository


class AlarmRepository(BaseRepository[Alarm]):
    model = Alarm

    def raise_alarm(self, alarm: Alarm) -> None:
        self._executor.execute_write(AlarmQueries.INSERT, asdict(alarm))

    def get_by_id(self, alarm_id: str) -> Alarm:
        row = self._executor.fetch_one(AlarmQueries.FIND_BY_ID, {"alarm_id": alarm_id})
        return self.require_one(row, not_found_message=f"Alarm '{alarm_id}' not found")

    def find_active(self) -> list[Alarm]:
        return self._map_many(self._executor.fetch_all(AlarmQueries.FIND_ACTIVE))

    def find_by_severity(self, severity: str) -> list[Alarm]:
        rows = self._executor.fetch_all(AlarmQueries.FIND_BY_SEVERITY, {"severity": severity})
        return self._map_many(rows)

    def find_by_entity(self, entity_type: str, entity_id: str) -> list[Alarm]:
        rows = self._executor.fetch_all(
            AlarmQueries.FIND_BY_ENTITY, {"entity_type": entity_type, "entity_id": entity_id}
        )
        return self._map_many(rows)

    def find_all(self) -> list[Alarm]:
        return self._map_many(self._executor.fetch_all(AlarmQueries.FIND_ALL))

    def clear_alarm(self, alarm_id: str, *, cleared_at: str) -> int:
        return self._executor.execute_write(
            AlarmQueries.CLEAR_ALARM, {"alarm_id": alarm_id, "cleared_at": cleared_at}
        )

    def count_active(self) -> int:
        row = self._executor.fetch_one(AlarmQueries.COUNT_ACTIVE)
        return int(row["c"]) if row else 0

    def count(self) -> int:
        row = self._executor.fetch_one(AlarmQueries.COUNT_ALL)
        return int(row["c"]) if row else 0
