from __future__ import annotations

from dataclasses import asdict

from framework.database.models import Tenant
from framework.database.queries import TenantQueries
from framework.database.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    model = Tenant

    def create(self, tenant: Tenant) -> None:
        self._executor.execute_write(TenantQueries.INSERT, asdict(tenant))

    def get_by_id(self, tenant_id: str) -> Tenant:
        row = self._executor.fetch_one(TenantQueries.FIND_BY_ID, {"tenant_id": tenant_id})
        return self.require_one(row, not_found_message=f"Tenant '{tenant_id}' not found")

    def find_by_code(self, tenant_code: str) -> Tenant | None:
        row = self._executor.fetch_one(TenantQueries.FIND_BY_CODE, {"tenant_code": tenant_code})
        return self._map_one(row)

    def find_by_status(self, status: str) -> list[Tenant]:
        rows = self._executor.fetch_all(TenantQueries.FIND_BY_STATUS, {"status": status})
        return self._map_many(rows)

    def find_all(self) -> list[Tenant]:
        return self._map_many(self._executor.fetch_all(TenantQueries.FIND_ALL))

    def update_status(self, tenant_id: str, status: str) -> int:
        return self._executor.execute_write(
            TenantQueries.UPDATE_STATUS, {"tenant_id": tenant_id, "status": status}
        )

    def delete(self, tenant_id: str) -> int:
        return self._executor.execute_write(TenantQueries.DELETE_BY_ID, {"tenant_id": tenant_id})

    def count(self) -> int:
        row = self._executor.fetch_one(TenantQueries.COUNT_ALL)
        return int(row["c"]) if row else 0
