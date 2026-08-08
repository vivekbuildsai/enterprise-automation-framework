from __future__ import annotations

from dataclasses import asdict

from framework.database.models import Network
from framework.database.queries import NetworkQueries
from framework.database.repositories.base_repository import BaseRepository


class NetworkRepository(BaseRepository[Network]):
    model = Network

    def create(self, network: Network) -> None:
        self._executor.execute_write(NetworkQueries.INSERT, asdict(network))

    def get_by_id(self, network_id: str) -> Network:
        row = self._executor.fetch_one(NetworkQueries.FIND_BY_ID, {"network_id": network_id})
        return self.require_one(row, not_found_message=f"Network '{network_id}' not found")

    def find_by_tenant(self, tenant_id: str) -> list[Network]:
        rows = self._executor.fetch_all(NetworkQueries.FIND_BY_TENANT, {"tenant_id": tenant_id})
        return self._map_many(rows)

    def find_by_ota_region(self, ota_region: str) -> list[Network]:
        rows = self._executor.fetch_all(
            NetworkQueries.FIND_BY_OTA_REGION, {"ota_region": ota_region}
        )
        return self._map_many(rows)

    def find_all(self) -> list[Network]:
        return self._map_many(self._executor.fetch_all(NetworkQueries.FIND_ALL))

    def update_status(self, network_id: str, status: str) -> int:
        return self._executor.execute_write(
            NetworkQueries.UPDATE_STATUS, {"network_id": network_id, "status": status}
        )

    def delete(self, network_id: str) -> int:
        return self._executor.execute_write(NetworkQueries.DELETE_BY_ID, {"network_id": network_id})

    def count(self) -> int:
        row = self._executor.fetch_one(NetworkQueries.COUNT_ALL)
        return int(row["c"]) if row else 0
