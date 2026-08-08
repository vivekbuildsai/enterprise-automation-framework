from __future__ import annotations

from dataclasses import asdict

from framework.database.models import SteeringZone
from framework.database.queries import SteeringQueries
from framework.database.repositories.base_repository import BaseRepository


class SteeringRepository(BaseRepository[SteeringZone]):
    """DB access for the Steering of Roaming domain — the persistence
    counterpart to `SteeringOverviewPage` (`docs/PageObjectDesign.md`) and
    the future `SteeringValidator` (`framework/database/validators`).
    """

    model = SteeringZone

    def create(self, zone: SteeringZone) -> None:
        self._executor.execute_write(SteeringQueries.INSERT, asdict(zone))

    def get_by_id(self, zone_id: str) -> SteeringZone:
        row = self._executor.fetch_one(SteeringQueries.FIND_BY_ID, {"zone_id": zone_id})
        return self.require_one(row, not_found_message=f"Steering zone '{zone_id}' not found")

    def find_by_tenant(self, tenant_id: str) -> list[SteeringZone]:
        rows = self._executor.fetch_all(SteeringQueries.FIND_BY_TENANT, {"tenant_id": tenant_id})
        return self._map_many(rows)

    def find_by_network(self, network_id: str) -> list[SteeringZone]:
        rows = self._executor.fetch_all(SteeringQueries.FIND_BY_NETWORK, {"network_id": network_id})
        return self._map_many(rows)

    def find_with_leakage(self, tenant_id: str) -> list[SteeringZone]:
        rows = self._executor.fetch_all(SteeringQueries.FIND_WITH_LEAKAGE, {"tenant_id": tenant_id})
        return self._map_many(rows)

    def find_anti_sor(self, tenant_id: str) -> list[SteeringZone]:
        rows = self._executor.fetch_all(SteeringQueries.FIND_ANTI_SOR, {"tenant_id": tenant_id})
        return self._map_many(rows)

    def find_all(self) -> list[SteeringZone]:
        return self._map_many(self._executor.fetch_all(SteeringQueries.FIND_ALL))

    def update_status(
        self, zone_id: str, status: str, *, modified_by: str, modified_date: str
    ) -> int:
        return self._executor.execute_write(
            SteeringQueries.UPDATE_STATUS,
            {
                "zone_id": zone_id,
                "status": status,
                "modified_by": modified_by,
                "modified_date": modified_date,
            },
        )

    def delete(self, zone_id: str) -> int:
        return self._executor.execute_write(SteeringQueries.DELETE_BY_ID, {"zone_id": zone_id})

    def count(self) -> int:
        row = self._executor.fetch_one(SteeringQueries.COUNT_ALL)
        return int(row["c"]) if row else 0

    def total_roamer_count(self, tenant_id: str) -> int:
        row = self._executor.fetch_one(
            SteeringQueries.SUM_ROAMER_COUNT_BY_TENANT, {"tenant_id": tenant_id}
        )
        return int(row["total"]) if row else 0
