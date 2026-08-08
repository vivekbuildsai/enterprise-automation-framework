from __future__ import annotations

from dataclasses import asdict

from framework.database.models import AuditLogEntry
from framework.database.queries import AuditQueries
from framework.database.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLogEntry]):
    """DB access for the application's own audit trail (distinct from
    `framework.database.audit.AuditLogger`, which logs this framework's own
    activity — see that module's docstring).
    """

    model = AuditLogEntry

    def record(self, entry: AuditLogEntry) -> None:
        self._executor.execute_write(AuditQueries.INSERT, asdict(entry))

    def get_by_id(self, audit_id: str) -> AuditLogEntry:
        row = self._executor.fetch_one(AuditQueries.FIND_BY_ID, {"audit_id": audit_id})
        return self.require_one(row, not_found_message=f"Audit entry '{audit_id}' not found")

    def find_by_entity(self, entity_type: str, entity_id: str) -> list[AuditLogEntry]:
        rows = self._executor.fetch_all(
            AuditQueries.FIND_BY_ENTITY, {"entity_type": entity_type, "entity_id": entity_id}
        )
        return self._map_many(rows)

    def find_by_performer(self, performed_by: str) -> list[AuditLogEntry]:
        rows = self._executor.fetch_all(
            AuditQueries.FIND_BY_PERFORMER, {"performed_by": performed_by}
        )
        return self._map_many(rows)

    def find_all(self) -> list[AuditLogEntry]:
        return self._map_many(self._executor.fetch_all(AuditQueries.FIND_ALL))

    def count(self) -> int:
        row = self._executor.fetch_one(AuditQueries.COUNT_ALL)
        return int(row["c"]) if row else 0
