from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from framework.discovery import DatabaseDiscoveryEngine

pytestmark = pytest.mark.discovery


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE tenants ("
                "tenant_id VARCHAR PRIMARY KEY, "
                "name VARCHAR NOT NULL, "
                "created_at VARCHAR)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE subscribers ("
                "subscriber_id VARCHAR PRIMARY KEY, "
                "tenant_id VARCHAR REFERENCES tenants(tenant_id), "
                "status VARCHAR)"
            )
        )
    yield engine
    engine.dispose()


def test_discover_tables_finds_every_table(engine) -> None:
    tables = DatabaseDiscoveryEngine(engine).discover_tables()
    names = {t.name for t in tables}
    assert names == {"tenants", "subscribers"}


def test_discover_tables_captures_primary_keys(engine) -> None:
    tables = {t.name: t for t in DatabaseDiscoveryEngine(engine).discover_tables()}
    tenant_id_col = next(c for c in tables["tenants"].columns if c.name == "tenant_id")
    assert tenant_id_col.primary_key is True

    name_col = next(c for c in tables["tenants"].columns if c.name == "name")
    assert name_col.primary_key is False


def test_discover_tables_captures_foreign_keys(engine) -> None:
    tables = {t.name: t for t in DatabaseDiscoveryEngine(engine).discover_tables()}
    assert len(tables["subscribers"].foreign_keys) == 1
    assert "tenants" in tables["subscribers"].foreign_keys[0]


def test_discover_tables_never_invents_a_table(engine) -> None:
    tables = DatabaseDiscoveryEngine(engine).discover_tables()
    assert all(t.name in {"tenants", "subscribers"} for t in tables)
