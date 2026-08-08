from __future__ import annotations

import pytest

from framework.database.repositories import TenantRepository
from framework.database.utilities import QueryExecutor
from framework.testdata.builders import UserBuilder
from framework.testdata.scenarios import ScenarioLibrary
from framework.testdata.seed import ApiSeeder, DatabaseSeeder, SeedOrchestrator

pytestmark = [
    pytest.mark.testdata,
    pytest.mark.database,
    pytest.mark.integration,
    pytest.mark.hybrid,
]


def test_seed_orchestrator_seeds_database_only_when_no_api_payloads(
    db_schema, database_manager, db_key, db_connection
):
    orchestrator = SeedOrchestrator(DatabaseSeeder(database_manager, db_key))
    scenario = ScenarioLibrary.new_subscriber()

    handle = orchestrator.seed(scenario)

    assert handle.scenario_name == "new_subscriber"
    assert handle.database_entities
    assert handle.api_records == []

    tenant = scenario.get("tenant")
    executor = QueryExecutor(db_connection, db_key=db_key, dialect="sqlite")
    assert TenantRepository(executor).get_by_id(tenant.tenant_id) is not None


def test_seed_orchestrator_seeds_database_and_real_api_together(
    db_schema, database_manager, db_key, api_client
):
    database_seeder = DatabaseSeeder(database_manager, db_key)
    api_seeder = ApiSeeder(api_client, "/users/add")
    orchestrator = SeedOrchestrator(database_seeder, api_seeder)

    scenario = ScenarioLibrary.new_subscriber()
    user = UserBuilder().build()

    handle = orchestrator.seed(scenario, api_payloads=[user.to_api_create_request()])

    assert handle.database_entities
    assert len(handle.api_records) == 1
    assert "id" in handle.api_records[0]
