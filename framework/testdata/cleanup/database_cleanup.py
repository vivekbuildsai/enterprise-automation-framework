from __future__ import annotations

from typing import Any

from framework.database.connection import DatabaseManager
from framework.database.models import Network, SteeringZone, Subscriber, Tenant
from framework.database.repositories import (
    NetworkRepository,
    SteeringRepository,
    SubscriberRepository,
    TenantRepository,
)
from framework.database.services import UnitOfWork
from framework.logger import get_logger

_logger = get_logger("DatabaseCleanupService")

# entity type -> (RepositoryClass, delete_method_name, id_field_name).
# Alarms are intentionally excluded: `AlarmRepository` has no `delete()`,
# only `clear_alarm()` — matching real alarm-lifecycle semantics (an alarm
# is cleared, not deleted).
_DELETE_MAP: dict[type, tuple[type, str, str]] = {
    Tenant: (TenantRepository, "delete", "tenant_id"),
    Network: (NetworkRepository, "delete", "network_id"),
    Subscriber: (SubscriberRepository, "delete", "subscriber_id"),
    SteeringZone: (SteeringRepository, "delete", "zone_id"),
}


class DatabaseCleanupService:
    """Deletes specific TDM-seeded entities via the repository layer,
    inside one `UnitOfWork` so a scenario's rows are removed atomically —
    the counterpart to `framework.testdata.seed.DatabaseSeeder`.
    """

    def __init__(self, db_manager: DatabaseManager, db_key: str, *, environment: str = "") -> None:
        self._db_manager = db_manager
        self._db_key = db_key
        self._environment = environment

    def delete(self, entities: list[Any]) -> None:
        with UnitOfWork(self._db_manager, self._db_key, environment=self._environment) as uow:
            for entity in entities:
                entity_type = type(entity)
                if entity_type not in _DELETE_MAP:
                    _logger.debug(f"No cleanup mapping for '{entity_type.__name__}' — skipping")
                    continue
                repository_cls, delete_method, id_field = _DELETE_MAP[entity_type]
                repository: Any = uow.repository(repository_cls)
                entity_id = getattr(entity, id_field)
                getattr(repository, delete_method)(entity_id)
