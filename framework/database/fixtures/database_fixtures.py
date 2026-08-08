from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy.engine import Connection

from framework.config import EnvironmentSettings
from framework.database.connection import DatabaseManager
from framework.database.repositories import (
    AlarmRepository,
    AuditRepository,
    NetworkRepository,
    SteeringRepository,
    SubscriberRepository,
    SystemRepository,
    TenantRepository,
)
from framework.database.services import SeedManager, SeedResult, UnitOfWork
from framework.database.utilities.cleanup_manager import CleanupManager
from framework.database.utilities.query_executor import QueryExecutor
from framework.database.utilities.schema_manager import SchemaManager

_DEFAULT_DB_KEY = "subscriber_db"


@pytest.fixture(scope="session")
def database_manager(settings: EnvironmentSettings) -> Generator[DatabaseManager, None, None]:
    """Session-scoped so every test in a run shares one engine (and its
    connection pool) per database — the same "one client, reused" pattern
    `api_client`'s underlying `httpx.Client` follows, just at session scope
    since engine creation (and its driver-availability check) is
    comparatively expensive to redo per test.
    """
    manager = DatabaseManager(settings)
    yield manager
    manager.dispose_all()


@pytest.fixture
def db_key() -> str:
    """Which entry in `settings.database` a test targets. Override at the
    test/module level (`@pytest.fixture def db_key(): return "other_db"`) to
    point every fixture in this file at a different database without
    touching test bodies — the same pattern `api_service_key` uses for the
    API layer.
    """
    return _DEFAULT_DB_KEY


@pytest.fixture
def db_connection(
    database_manager: DatabaseManager, db_key: str
) -> Generator[Connection, None, None]:
    """Function-scoped connection — like the UI layer's `page` fixture, each
    test gets its own so state (an open transaction, a temp table) never
    leaks between tests even though they share one pooled engine.
    """
    with database_manager.connection(db_key) as conn:
        yield conn


@pytest.fixture
def db_executor(
    db_connection: Connection,
    database_manager: DatabaseManager,
    settings: EnvironmentSettings,
    db_key: str,
) -> QueryExecutor:
    config = database_manager.config_for(db_key)
    return QueryExecutor(
        db_connection,
        db_key=db_key,
        dialect=config.dialect.value,
        environment=settings.environment.value,
    )


@pytest.fixture
def unit_of_work_factory(
    database_manager: DatabaseManager, settings: EnvironmentSettings, db_key: str
) -> Any:
    """Returns a zero-arg-friendly factory (`uow_factory(mode=...)`) rather
    than a single `UnitOfWork` instance, since a `UnitOfWork` is a
    one-shot context manager — most tests that need one need to open it more
    than once (e.g. one per assertion phase).
    """

    def _factory(**kwargs: Any) -> UnitOfWork:
        return UnitOfWork(
            database_manager, db_key, environment=settings.environment.value, **kwargs
        )

    return _factory


@pytest.fixture
def subscriber_repository(db_executor: QueryExecutor) -> SubscriberRepository:
    return SubscriberRepository(db_executor)


@pytest.fixture
def tenant_repository(db_executor: QueryExecutor) -> TenantRepository:
    return TenantRepository(db_executor)


@pytest.fixture
def network_repository(db_executor: QueryExecutor) -> NetworkRepository:
    return NetworkRepository(db_executor)


@pytest.fixture
def steering_repository(db_executor: QueryExecutor) -> SteeringRepository:
    return SteeringRepository(db_executor)


@pytest.fixture
def audit_repository(db_executor: QueryExecutor) -> AuditRepository:
    return AuditRepository(db_executor)


@pytest.fixture
def alarm_repository(db_executor: QueryExecutor) -> AlarmRepository:
    return AlarmRepository(db_executor)


@pytest.fixture
def system_repository(db_executor: QueryExecutor) -> SystemRepository:
    return SystemRepository(db_executor)


@pytest.fixture
def db_schema(db_connection: Connection, db_executor: QueryExecutor) -> Generator[None, None, None]:
    """Creates the demo schema (`SchemaManager.create_all`) for this test and
    truncates every table on teardown (`CleanupManager.truncate_all`) —
    tables persist across tests (cheap: `CREATE TABLE IF NOT EXISTS`) but no
    row does, so tests never see another test's leftover data.
    """
    SchemaManager.create_all(db_executor)
    db_connection.commit()
    yield
    CleanupManager.truncate_all(db_executor)
    db_connection.commit()


@pytest.fixture
def seeded_baseline(
    db_schema: None, db_connection: Connection, db_executor: QueryExecutor
) -> SeedResult:
    """A ready-to-use baseline dataset (one tenant, one network, 3
    subscribers, 3 steering zones with fixed leakage/anti-SoR combinations)
    for tests that need real rows without hand-writing fixture data — see
    `SeedManager.seed_baseline`.
    """
    result = SeedManager(db_executor).seed_baseline()
    db_connection.commit()
    return result
