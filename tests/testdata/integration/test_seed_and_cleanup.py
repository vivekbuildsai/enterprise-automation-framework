from __future__ import annotations

import pytest

from framework.database.exceptions import RepositoryError
from framework.database.repositories import (
    SteeringRepository,
    SubscriberRepository,
    TenantRepository,
)
from framework.database.utilities import QueryExecutor
from framework.testdata.builders import TenantBuilder
from framework.testdata.cleanup import CleanupRegistry, DatabaseCleanupService
from framework.testdata.scenarios import ScenarioLibrary
from framework.testdata.seed import DatabaseSeeder

pytestmark = [pytest.mark.testdata, pytest.mark.database, pytest.mark.integration]


def test_database_seeder_persists_a_single_entity(
    db_schema, database_manager, db_key, db_connection
):
    seeder = DatabaseSeeder(database_manager, db_key)
    tenant = TenantBuilder().build()

    seeder.seed([tenant])

    executor = QueryExecutor(db_connection, db_key=db_key, dialect="sqlite")
    assert TenantRepository(executor).get_by_id(tenant.tenant_id).tenant_id == tenant.tenant_id


def test_database_seeder_seed_scenario_skips_non_db_entities(db_schema, database_manager, db_key):
    seeder = DatabaseSeeder(database_manager, db_key)
    scenario = ScenarioLibrary.roaming_subscriber()  # includes a non-DB SimCard

    seeded = seeder.seed_scenario(scenario)

    assert "SimCard" not in [type(e).__name__ for e in seeded]
    assert "Subscriber" in [type(e).__name__ for e in seeded]


def test_database_seeder_seed_scenario_strict_mode_raises_on_non_db_entities(
    db_schema, database_manager, db_key
):
    from framework.exceptions import TestDataError

    seeder = DatabaseSeeder(database_manager, db_key)
    scenario = ScenarioLibrary.roaming_subscriber()

    with pytest.raises(TestDataError):
        seeder.seed_scenario(scenario, strict=True)


def test_database_seeder_seeds_scenario_transactionally(
    db_schema, database_manager, db_key, db_connection
):
    seeder = DatabaseSeeder(database_manager, db_key)
    scenario = ScenarioLibrary.premium_customer()

    seeder.seed_scenario(scenario)

    executor = QueryExecutor(db_connection, db_key=db_key, dialect="sqlite")
    tenant = scenario.get("tenant")
    subscriber = scenario.get("subscriber")
    assert TenantRepository(executor).get_by_id(tenant.tenant_id) is not None
    assert SubscriberRepository(executor).get_by_id(subscriber.subscriber_id).cos == "Gold"


def test_database_cleanup_service_removes_seeded_entities(
    db_schema, database_manager, db_key, db_connection
):
    seeder = DatabaseSeeder(database_manager, db_key)
    cleanup = DatabaseCleanupService(database_manager, db_key)
    tenant = TenantBuilder().build()
    seeder.seed([tenant])

    cleanup.delete([tenant])

    executor = QueryExecutor(db_connection, db_key=db_key, dialect="sqlite")
    with pytest.raises(RepositoryError):
        TenantRepository(executor).get_by_id(tenant.tenant_id)


def test_cleanup_registry_runs_registered_callback_in_lifo_order(
    db_schema, database_manager, db_key
):
    order: list[str] = []
    registry = CleanupRegistry()
    registry.register(lambda: order.append("first"))
    registry.register(lambda: order.append("second"))

    registry.execute_all()

    assert order == ["second", "first"]


def test_cleanup_registry_collects_errors_without_stopping(db_schema, database_manager, db_key):
    registry = CleanupRegistry()
    ran: list[str] = []
    registry.register(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    registry.register(lambda: ran.append("ok"))

    errors = registry.execute_all()

    assert len(errors) == 1
    assert ran == ["ok"]


def test_full_seed_then_cleanup_round_trip_via_scenario(
    db_schema, database_manager, db_key, db_connection
):
    seeder = DatabaseSeeder(database_manager, db_key)
    cleanup = DatabaseCleanupService(database_manager, db_key)
    scenario = ScenarioLibrary.roaming_subscriber()

    seeded = seeder.seed_scenario(scenario)
    executor = QueryExecutor(db_connection, db_key=db_key, dialect="sqlite")
    zone = scenario.get("zone")
    assert SteeringRepository(executor).get_by_id(zone.zone_id) is not None

    cleanup.delete(seeded)

    with pytest.raises(RepositoryError):
        SteeringRepository(executor).get_by_id(zone.zone_id)
