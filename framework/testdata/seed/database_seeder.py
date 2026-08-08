from __future__ import annotations

from typing import Any

from framework.database.connection import DatabaseManager
from framework.database.models import Alarm, Network, SteeringZone, Subscriber, Tenant
from framework.database.repositories import (
    AlarmRepository,
    NetworkRepository,
    SteeringRepository,
    SubscriberRepository,
    TenantRepository,
)
from framework.database.services import UnitOfWork
from framework.exceptions import TestDataError
from framework.logger import get_logger

_logger = get_logger("DatabaseSeeder")

_REPOSITORY_MAP: dict[type, tuple[type, str]] = {
    Tenant: (TenantRepository, "create"),
    Network: (NetworkRepository, "create"),
    Subscriber: (SubscriberRepository, "create"),
    SteeringZone: (SteeringRepository, "create"),
    Alarm: (AlarmRepository, "raise_alarm"),
}


class DatabaseSeeder:
    """Seeds TDM-builder-produced entities (`Tenant`/`Network`/
    `Subscriber`/`SteeringZone`/`Alarm`) into the database via the
    repository layer, inside one `UnitOfWork` so a scenario's entities
    commit — or roll back — together.

    Distinct from `framework.database.services.SeedManager`: that seeds one
    fixed baseline dataset; this seeds *whatever* entities the TDM layer
    built for a specific test/scenario.
    """

    def __init__(self, db_manager: DatabaseManager, db_key: str, *, environment: str = "") -> None:
        self._db_manager = db_manager
        self._db_key = db_key
        self._environment = environment

    def seed(self, entities: list[Any]) -> None:
        """Seeds every entity. Raises `TestDataError` if any entity's type
        has no repository mapping — use `seed_scenario(strict=False)`
        instead when the entities may legitimately include non-DB types
        (e.g. a `SimCard`/`UserProfile`/`BillingRecord` alongside DB ones).
        """
        with UnitOfWork(self._db_manager, self._db_key, environment=self._environment) as uow:
            for entity in entities:
                entity_type = type(entity)
                if entity_type not in _REPOSITORY_MAP:
                    raise TestDataError(
                        f"No repository mapping for entity type '{entity_type.__name__}' — "
                        f"mapped types: {[t.__name__ for t in _REPOSITORY_MAP]}"
                    )
                repository_cls, create_method = _REPOSITORY_MAP[entity_type]
                repository: Any = uow.repository(repository_cls)
                getattr(repository, create_method)(entity)

    def seed_scenario(self, scenario: Any, *, strict: bool = False) -> list[Any]:
        """Seeds every entity in a `Scenario`, flattening any list-valued
        entities (e.g. `enterprise_customer`'s `subscribers` list). Entities
        with no DB repository mapping (SIM cards, users, billing records)
        are skipped by default — set `strict=True` to raise instead.
        Returns the list of entities that were actually seeded.
        """
        flattened: list[Any] = []
        for value in scenario.entities.values():
            flattened.extend(value if isinstance(value, list) else [value])

        seedable = [e for e in flattened if type(e) in _REPOSITORY_MAP]
        skipped = [e for e in flattened if type(e) not in _REPOSITORY_MAP]
        if skipped and strict:
            names = [type(e).__name__ for e in skipped]
            raise TestDataError(f"Scenario '{scenario.name}' has non-DB entities: {names}")
        if skipped:
            _logger.debug(
                f"Scenario '{scenario.name}': skipping {len(skipped)} entity type(s) with no "
                f"DB repository mapping ({[type(e).__name__ for e in skipped]})"
            )

        self.seed(seedable)
        return seedable
