from __future__ import annotations

import pytest
from sqlalchemy.engine import Connection

from framework.database.exceptions import RepositoryError
from framework.database.models import (
    Alarm,
    AuditLogEntry,
    Network,
    SteeringZone,
    Subscriber,
    SystemConfig,
    Tenant,
)
from framework.database.repositories import (
    AlarmRepository,
    AuditRepository,
    NetworkRepository,
    SteeringRepository,
    SubscriberRepository,
    SystemRepository,
    TenantRepository,
)

pytestmark = [pytest.mark.regression, pytest.mark.database]


def test_tenant_repository_crud(
    db_schema: None, db_connection: Connection, tenant_repository: TenantRepository
) -> None:
    tenant_repository.create(
        Tenant(
            tenant_id="T1",
            tenant_code="A01",
            tenant_name="Tenant A01",
            status="ACTIVE",
            created_at="t",
        )
    )
    db_connection.commit()

    assert tenant_repository.get_by_id("T1").tenant_code == "A01"
    assert tenant_repository.find_by_code("A01") is not None
    assert tenant_repository.find_by_code("MISSING") is None
    assert tenant_repository.count() == 1

    tenant_repository.update_status("T1", "SUSPENDED")
    db_connection.commit()
    assert tenant_repository.get_by_id("T1").status == "SUSPENDED"
    assert [t.tenant_id for t in tenant_repository.find_by_status("SUSPENDED")] == ["T1"]

    tenant_repository.delete("T1")
    db_connection.commit()
    assert tenant_repository.count() == 0

    with pytest.raises(RepositoryError):
        tenant_repository.get_by_id("T1")


def test_network_repository_crud(
    db_schema: None, db_connection: Connection, network_repository: NetworkRepository
) -> None:
    network_repository.create(
        Network(
            network_id="N1",
            network_code="N1",
            network_name="Network 1",
            tenant_id="T1",
            ota_region="EMEA",
            status="ACTIVE",
        )
    )
    db_connection.commit()

    assert network_repository.get_by_id("N1").ota_region == "EMEA"
    assert [n.network_id for n in network_repository.find_by_tenant("T1")] == ["N1"]
    assert [n.network_id for n in network_repository.find_by_ota_region("EMEA")] == ["N1"]
    assert network_repository.find_by_ota_region("APAC") == []

    with pytest.raises(RepositoryError):
        network_repository.get_by_id("MISSING")


def test_subscriber_repository_crud(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    subscriber_repository.create(
        Subscriber(
            subscriber_id="S1",
            msisdn="447700900123",
            imsi="234000000000001",
            status="ACTIVE",
            cos="Gold",
            tenant_id="T1",
            network_id="N1",
            created_at="t",
            updated_at="t",
        )
    )
    db_connection.commit()

    assert subscriber_repository.find_by_msisdn("447700900123") is not None
    assert subscriber_repository.find_by_msisdn("does-not-exist") is None
    assert subscriber_repository.count_by_status("ACTIVE") == 1

    subscriber_repository.update_status("S1", "SUSPENDED", updated_at="t2")
    db_connection.commit()
    assert subscriber_repository.get_by_id("S1").status == "SUSPENDED"
    assert subscriber_repository.count_by_status("ACTIVE") == 0


def test_steering_repository_leakage_and_anti_sor_queries(
    db_schema: None, db_connection: Connection, steering_repository: SteeringRepository
) -> None:
    steering_repository.create(
        SteeringZone(
            zone_id="Z1",
            zone_code="Country_A",
            country="Country_A",
            tenant_id="T1",
            network_id="N1",
            tr_type="LBTR",
            cos="Gold",
            ota_region="EMEA",
            roamer_count=120,
            data_usage_mb=4500,
            leakage_flag=1,
            anti_sor_flag=0,
            status="ACTIVE",
            modified_by="Admin",
            modified_date="t",
        )
    )
    steering_repository.create(
        SteeringZone(
            zone_id="Z2",
            zone_code="Country_B",
            country="Country_B",
            tenant_id="T1",
            network_id="N1",
            tr_type="SRDC",
            cos="Silver",
            ota_region="EU",
            roamer_count=40,
            data_usage_mb=900,
            leakage_flag=0,
            anti_sor_flag=1,
            status="ACTIVE",
            modified_by="Admin",
            modified_date="t",
        )
    )
    db_connection.commit()

    assert [z.zone_id for z in steering_repository.find_with_leakage("T1")] == ["Z1"]
    assert [z.zone_id for z in steering_repository.find_anti_sor("T1")] == ["Z2"]
    assert steering_repository.total_roamer_count("T1") == 160
    assert steering_repository.get_by_id("Z1").has_leakage is True
    assert steering_repository.get_by_id("Z2").is_anti_sor is True


def test_audit_repository_record_and_query(
    db_schema: None, db_connection: Connection, audit_repository: AuditRepository
) -> None:
    audit_repository.record(
        AuditLogEntry(
            audit_id="A1",
            entity_type="SUBSCRIBER",
            entity_id="S1",
            action="STATUS_CHANGE",
            performed_by="Admin",
            performed_at="t",
            details="ACTIVE -> SUSPENDED",
        )
    )
    db_connection.commit()

    entries = audit_repository.find_by_entity("SUBSCRIBER", "S1")
    assert len(entries) == 1
    assert entries[0].action == "STATUS_CHANGE"
    assert audit_repository.find_by_performer("Admin")[0].audit_id == "A1"


def test_alarm_repository_raise_and_clear(
    db_schema: None, db_connection: Connection, alarm_repository: AlarmRepository
) -> None:
    alarm_repository.raise_alarm(
        Alarm(
            alarm_id="AL1",
            alarm_code="LEAK-001",
            severity="CRITICAL",
            entity_type="STEERING_ZONE",
            entity_id="Z1",
            status="ACTIVE",
            raised_at="t",
            cleared_at=None,
            description="Leakage detected",
        )
    )
    db_connection.commit()

    assert alarm_repository.count_active() == 1
    assert alarm_repository.find_by_severity("CRITICAL")[0].alarm_id == "AL1"

    alarm_repository.clear_alarm("AL1", cleared_at="t2")
    db_connection.commit()
    assert alarm_repository.count_active() == 0
    assert alarm_repository.get_by_id("AL1").status == "CLEARED"


def test_system_repository_crud(
    db_schema: None, db_connection: Connection, system_repository: SystemRepository
) -> None:
    system_repository.create(
        SystemConfig(
            config_id="C1",
            config_key="steering.leakage_threshold",
            config_value="5",
            category="steering",
            updated_by="Admin",
            updated_at="t",
        )
    )
    db_connection.commit()

    assert system_repository.get_by_key("steering.leakage_threshold").config_value == "5"
    system_repository.update_value(
        "steering.leakage_threshold", "10", updated_by="Admin", updated_at="t2"
    )
    db_connection.commit()
    assert system_repository.get_by_key("steering.leakage_threshold").config_value == "10"
    assert [c.config_key for c in system_repository.find_by_category("steering")] == [
        "steering.leakage_threshold"
    ]
