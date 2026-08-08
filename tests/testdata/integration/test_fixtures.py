from __future__ import annotations

import pytest

from framework.database.repositories import TenantRepository
from framework.database.utilities import QueryExecutor
from framework.exceptions import TestDataError

pytestmark = [pytest.mark.testdata, pytest.mark.database, pytest.mark.integration]


def test_seeded_scenario_fixture_seeds_into_the_database(
    seeded_scenario, db_schema, database_manager, db_key
):
    handle = seeded_scenario("premium_customer")
    tenant = next(e for e in handle.database_entities if type(e).__name__ == "Tenant")

    with database_manager.connection(db_key) as conn:
        executor = QueryExecutor(conn, db_key=db_key, dialect="sqlite")
        assert TenantRepository(executor).get_by_id(tenant.tenant_id).tenant_id == tenant.tenant_id


def test_seeded_scenario_registers_exactly_one_cleanup_callback(
    seeded_scenario, cleanup_registry, db_schema
):
    """`seeded_scenario` registers its teardown with the same
    `cleanup_registry` this test also received (both resolve to the one
    fixture instance for this test) — checking the registry's length here,
    before fixture teardown fires, is a self-contained way to confirm
    registration happened without depending on execution order across
    separate tests (see docs/CleanupStrategy.md for why that matters under
    parallel/xdist runs).
    """
    assert len(cleanup_registry) == 0
    seeded_scenario("new_subscriber")
    assert len(cleanup_registry) == 1


def test_load_dataset_fixture(load_dataset):
    data = load_dataset("subscriber_management/dev.json")
    assert "search_terms" in data


def test_build_scenario_fixture(build_scenario):
    scenario = build_scenario("blocked_subscriber")
    assert scenario.name == "blocked_subscriber"
    assert scenario.get("subscriber").status == "BLOCKED"


def test_build_scenario_fixture_raises_for_unknown_name(build_scenario):
    with pytest.raises(TestDataError):
        build_scenario("not_a_real_scenario")


def test_cleanup_registry_fixture_accepts_registrations(cleanup_registry):
    ran = []
    cleanup_registry.register(lambda: ran.append(True))
    assert len(cleanup_registry) == 1
