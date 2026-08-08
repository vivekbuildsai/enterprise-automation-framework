from __future__ import annotations

import pytest

from framework.testdata.factories import (
    AlarmFactory,
    BillingFactory,
    NetworkFactory,
    SimFactory,
    SteeringRuleFactory,
    SubscriberFactory,
    TenantFactory,
    UserFactory,
)

pytestmark = pytest.mark.testdata


def test_subscriber_factory_canned_variants() -> None:
    assert SubscriberFactory.active().status == "ACTIVE"
    assert SubscriberFactory.blocked().status == "BLOCKED"
    assert SubscriberFactory.suspended().status == "SUSPENDED"
    premium = SubscriberFactory.premium()
    assert premium.cos == "Gold"
    assert premium.status == "ACTIVE"


def test_subscriber_factory_new_is_active() -> None:
    assert SubscriberFactory.new().status == "ACTIVE"


def test_subscriber_factory_accepts_overrides() -> None:
    subscriber = SubscriberFactory.active(tenant_id="OVERRIDE-TENANT")
    assert subscriber.tenant_id == "OVERRIDE-TENANT"


def test_tenant_factory_canned_variants() -> None:
    assert TenantFactory.active().status == "ACTIVE"
    assert TenantFactory.suspended().status == "SUSPENDED"


def test_network_factory_region() -> None:
    network = NetworkFactory.in_region("APAC")
    assert network.ota_region == "APAC"
    assert network.status == "ACTIVE"


def test_steering_rule_factory_variants() -> None:
    assert SteeringRuleFactory.with_leakage().has_leakage is True
    assert SteeringRuleFactory.anti_sor().is_anti_sor is True
    failure = SteeringRuleFactory.network_failure()
    assert failure.status == "DEGRADED"
    assert failure.roamer_count == 0


def test_alarm_factory_network_failure() -> None:
    alarm = AlarmFactory.network_failure("NETWORK-42")
    assert alarm.entity_type == "NETWORK"
    assert alarm.entity_id == "NETWORK-42"
    assert alarm.severity == "CRITICAL"


def test_sim_factory_variants() -> None:
    assert SimFactory.active().status == "ACTIVE"
    assert SimFactory.inactive().status == "INACTIVE"
    assert SimFactory.blocked().status == "BLOCKED"


def test_billing_factory_variants() -> None:
    assert BillingFactory.paid().status == "PAID"
    assert BillingFactory.overdue().status == "OVERDUE"
    assert BillingFactory.error().status == "ERROR"


def test_user_factory_roles() -> None:
    assert UserFactory.administrator().role == "Administrator"
    assert UserFactory.operator().role == "Operator"
