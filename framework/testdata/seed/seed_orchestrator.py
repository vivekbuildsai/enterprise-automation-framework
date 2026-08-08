from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from framework.testdata.seed.api_seeder import ApiSeeder
from framework.testdata.seed.database_seeder import DatabaseSeeder


@dataclass(slots=True)
class SeedHandle:
    """What a seeding operation actually produced — handed to
    `framework.testdata.cleanup.CleanupRegistry` so cleanup code knows
    exactly what to tear down, without re-deriving it from the scenario.
    """

    scenario_name: str
    database_entities: list[Any] = field(default_factory=list)
    api_records: list[dict[str, Any]] = field(default_factory=list)


class SeedOrchestrator:
    """Coordinates seeding a `Scenario`'s entities across the database and
    (optionally) an API in one call — the caller doesn't need to know
    which of a scenario's entities belong to which layer, only that
    `orchestrator.seed(scenario)` makes the whole scenario exist wherever
    it needs to.
    """

    def __init__(
        self, database_seeder: DatabaseSeeder, api_seeder: ApiSeeder | None = None
    ) -> None:
        self._database_seeder = database_seeder
        self._api_seeder = api_seeder

    def seed(
        self,
        scenario: Any,
        *,
        api_payloads: list[dict[str, Any]] | None = None,
        strict: bool = False,
    ) -> SeedHandle:
        seeded_entities = self._database_seeder.seed_scenario(scenario, strict=strict)

        api_records: list[dict[str, Any]] = []
        if api_payloads and self._api_seeder is not None:
            api_records = self._api_seeder.seed_many(api_payloads)

        return SeedHandle(
            scenario_name=scenario.name,
            database_entities=seeded_entities,
            api_records=api_records,
        )
