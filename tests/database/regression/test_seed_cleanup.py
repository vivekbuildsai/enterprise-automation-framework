from __future__ import annotations

import pytest
from sqlalchemy.engine import Connection

from framework.database.repositories import (
    SteeringRepository,
    SubscriberRepository,
    TenantRepository,
)
from framework.database.services import SeedManager, SeedResult
from framework.database.utilities import CleanupManager, QueryExecutor, SchemaManager

pytestmark = [pytest.mark.regression, pytest.mark.database]


def test_seeded_baseline_creates_expected_rows(
    seeded_baseline: SeedResult,
    tenant_repository: TenantRepository,
    subscriber_repository: SubscriberRepository,
    steering_repository: SteeringRepository,
) -> None:
    assert seeded_baseline.tenant.tenant_id == "T-BASE"
    assert tenant_repository.count() == 1
    assert subscriber_repository.count() == 3
    assert steering_repository.count() == 3


def test_seeded_baseline_has_exactly_one_leakage_and_one_anti_sor_zone(
    seeded_baseline: SeedResult, steering_repository: SteeringRepository
) -> None:
    assert len(steering_repository.find_with_leakage("T-BASE")) == 1
    assert len(steering_repository.find_anti_sor("T-BASE")) == 1


def test_seed_manager_is_reusable_for_a_second_tenant(
    db_schema: None, db_connection: Connection, db_executor: QueryExecutor
) -> None:
    result = SeedManager(db_executor).seed_baseline(
        tenant_id="T-SECOND", network_id="N-SECOND", subscriber_count=1
    )
    db_connection.commit()
    assert result.tenant.tenant_id == "T-SECOND"
    assert len(result.subscribers) == 1


def test_cleanup_manager_truncates_every_table(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    SchemaManager.create_all(db_executor)
    SeedManager(db_executor).seed_baseline()
    db_connection.commit()
    assert db_executor.fetch_one("SELECT COUNT(*) AS c FROM tenants")["c"] == 1

    CleanupManager.truncate_all(db_executor)
    db_connection.commit()

    for table in ("tenants", "networks", "subscribers", "steering_zones"):
        assert db_executor.fetch_one(f"SELECT COUNT(*) AS c FROM {table}")["c"] == 0
