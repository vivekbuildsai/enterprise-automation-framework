from __future__ import annotations

from collections.abc import Callable, Generator

import pytest

from framework.config import EnvironmentSettings
from framework.database.connection import DatabaseManager
from framework.exceptions import TestDataError
from framework.testdata.cleanup import CleanupRegistry, DatabaseCleanupService
from framework.testdata.datasets import DatasetLoader
from framework.testdata.scenarios import Scenario, ScenarioLibrary
from framework.testdata.seed import DatabaseSeeder, SeedHandle


@pytest.fixture
def cleanup_registry() -> Generator[CleanupRegistry, None, None]:
    """Function-scoped — register any teardown callable
    (`cleanup_registry.register(lambda: ...)`) and it runs automatically
    after the test, in LIFO order, regardless of whether the test passed
    or failed. The first cleanup error (if any) is re-raised after every
    callback has had a chance to run, so a failing cleanup is visible
    without masking other callbacks' cleanup.
    """
    registry = CleanupRegistry()
    yield registry
    errors = registry.execute_all()
    if errors:
        raise errors[0]


@pytest.fixture
def database_seeder(
    database_manager: DatabaseManager, settings: EnvironmentSettings, db_key: str
) -> DatabaseSeeder:
    return DatabaseSeeder(database_manager, db_key, environment=settings.environment.value)


@pytest.fixture
def database_cleanup_service(
    database_manager: DatabaseManager, settings: EnvironmentSettings, db_key: str
) -> DatabaseCleanupService:
    return DatabaseCleanupService(database_manager, db_key, environment=settings.environment.value)


@pytest.fixture
def load_dataset() -> Callable[[str], object]:
    """`load_dataset("subscriber_management/dev.json")` — thin fixture
    wrapper over `DatasetLoader.load_json` so a test doesn't need its own
    import for the common case.
    """
    return DatasetLoader.load_json


@pytest.fixture
def build_scenario() -> Callable[[str], Scenario]:
    """`build_scenario("roaming_subscriber")` -> `Scenario` — looks up a
    named method on `ScenarioLibrary` by name, so tests can select a
    scenario by string (useful for parametrized tests) without importing
    `ScenarioLibrary` and reaching for the method directly.
    """

    def _build(name: str) -> Scenario:
        if not hasattr(ScenarioLibrary, name):
            raise TestDataError(f"No scenario named '{name}' in ScenarioLibrary")
        return getattr(ScenarioLibrary, name)()  # type: ignore[no-any-return]

    return _build


@pytest.fixture
def seeded_scenario(
    database_seeder: DatabaseSeeder,
    database_cleanup_service: DatabaseCleanupService,
    cleanup_registry: CleanupRegistry,
    build_scenario: Callable[[str], Scenario],
) -> Callable[..., SeedHandle]:
    """`handle = seeded_scenario("roaming_subscriber")` — builds the named
    `ScenarioLibrary` scenario, seeds its DB-backed entities, and registers
    their cleanup automatically via `cleanup_registry`. This is the single
    fixture that ties together Scenario Library + Data Seeding + Data
    Cleanup: a UI/API/DB test calls this once and never has to think about
    teardown.
    """

    def _seed(name: str, *, strict: bool = False) -> SeedHandle:
        scenario = build_scenario(name)
        seeded_entities = database_seeder.seed_scenario(scenario, strict=strict)
        cleanup_registry.register(lambda: database_cleanup_service.delete(seeded_entities))
        return SeedHandle(scenario_name=scenario.name, database_entities=seeded_entities)

    return _seed
