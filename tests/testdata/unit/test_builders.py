from __future__ import annotations

import pytest

from framework.testdata.builders import (
    AlarmBuilder,
    BillingBuilder,
    NetworkBuilder,
    SIMBuilder,
    SteeringRuleBuilder,
    SubscriberBuilder,
    TenantBuilder,
    UserBuilder,
)

pytestmark = pytest.mark.testdata


def test_tenant_builder_fluent_chain_and_defaults() -> None:
    tenant = TenantBuilder().with_tenant_code("A01").active().build()
    assert tenant.tenant_code == "A01"
    assert tenant.status == "ACTIVE"
    assert tenant.tenant_id  # generated default


def test_tenant_builder_suspended() -> None:
    assert TenantBuilder().suspended().build().status == "SUSPENDED"


def test_network_builder_defaults_and_overrides() -> None:
    network = NetworkBuilder().with_tenant_id("T1").with_ota_region("APAC").build()
    assert network.tenant_id == "T1"
    assert network.ota_region == "APAC"
    assert network.status == "ACTIVE"


def test_subscriber_builder_status_shortcuts() -> None:
    assert SubscriberBuilder().active().build().status == "ACTIVE"
    assert SubscriberBuilder().suspended().build().status == "SUSPENDED"
    assert SubscriberBuilder().blocked().build().status == "BLOCKED"


def test_subscriber_builder_generates_telecom_identifiers_by_default() -> None:
    subscriber = SubscriberBuilder().build()
    assert subscriber.msisdn.isdigit()
    assert subscriber.imsi.isdigit()
    assert len(subscriber.imsi) == 15


def test_subscriber_builder_explicit_overrides_win() -> None:
    subscriber = SubscriberBuilder().with_msisdn("447700900123").build()
    assert subscriber.msisdn == "447700900123"


def test_steering_rule_builder_leakage_and_anti_sor_flags() -> None:
    zone = SteeringRuleBuilder().with_leakage().build()
    assert zone.has_leakage is True
    assert zone.is_anti_sor is False

    zone2 = SteeringRuleBuilder().with_anti_sor(is_anti_sor=False).build()
    assert zone2.is_anti_sor is False


def test_alarm_builder_critical_and_cleared() -> None:
    alarm = AlarmBuilder().critical().active().build()
    assert alarm.severity == "CRITICAL"
    assert alarm.status == "ACTIVE"
    assert alarm.cleared_at is None

    cleared = AlarmBuilder().cleared().build()
    assert cleared.status == "CLEARED"
    assert cleared.cleared_at is not None


def test_sim_builder_active_sets_activation_date() -> None:
    sim = SIMBuilder().active().build()
    assert sim.status == "ACTIVE"
    assert sim.activation_date is not None


def test_sim_builder_inactive_clears_activation_date() -> None:
    sim = SIMBuilder().inactive().build()
    assert sim.status == "INACTIVE"
    assert sim.activation_date is None


def test_billing_builder_status_shortcuts() -> None:
    assert BillingBuilder().paid().build().status == "PAID"
    assert BillingBuilder().overdue().build().status == "OVERDUE"
    error_bill = BillingBuilder().billing_error().build()
    assert error_bill.status == "ERROR"


def test_user_builder_role_and_api_request_mapping() -> None:
    user = UserBuilder().as_administrator().with_email("a@b.com").build()
    assert user.role == "Administrator"
    request = user.to_api_create_request()
    assert request["email"] == "a@b.com"
    assert "firstName" in request and "lastName" in request


def test_build_many_produces_distinct_records() -> None:
    subscribers = SubscriberBuilder().gold_tier().build_many(5)
    assert len(subscribers) == 5
    assert len({s.subscriber_id for s in subscribers}) == 5
    assert all(s.cos == "Gold" for s in subscribers)


def test_build_many_shares_explicit_overrides_across_records() -> None:
    zones = SteeringRuleBuilder().with_tenant_id("SHARED-TENANT").build_many(3)
    assert all(z.tenant_id == "SHARED-TENANT" for z in zones)
    assert len({z.zone_id for z in zones}) == 3
