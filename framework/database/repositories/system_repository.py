from __future__ import annotations

from dataclasses import asdict

from framework.database.models import SystemConfig
from framework.database.queries import SystemQueries
from framework.database.repositories.base_repository import BaseRepository


class SystemRepository(BaseRepository[SystemConfig]):
    model = SystemConfig

    def create(self, config: SystemConfig) -> None:
        self._executor.execute_write(SystemQueries.INSERT, asdict(config))

    def get_by_key(self, config_key: str) -> SystemConfig:
        row = self._executor.fetch_one(SystemQueries.FIND_BY_KEY, {"config_key": config_key})
        return self.require_one(row, not_found_message=f"System config '{config_key}' not found")

    def find_by_category(self, category: str) -> list[SystemConfig]:
        rows = self._executor.fetch_all(SystemQueries.FIND_BY_CATEGORY, {"category": category})
        return self._map_many(rows)

    def find_all(self) -> list[SystemConfig]:
        return self._map_many(self._executor.fetch_all(SystemQueries.FIND_ALL))

    def update_value(
        self, config_key: str, config_value: str, *, updated_by: str, updated_at: str
    ) -> int:
        return self._executor.execute_write(
            SystemQueries.UPDATE_VALUE,
            {
                "config_key": config_key,
                "config_value": config_value,
                "updated_by": updated_by,
                "updated_at": updated_at,
            },
        )

    def count(self) -> int:
        row = self._executor.fetch_one(SystemQueries.COUNT_ALL)
        return int(row["c"]) if row else 0
