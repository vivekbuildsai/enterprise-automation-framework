from __future__ import annotations

import pytest

from framework.testdata.scenarios import ScenarioLibrary

pytestmark = pytest.mark.testdata

_ALL_SCENARIOS = [
    "new_subscriber",
    "roaming_subscriber",
    "blocked_subscriber",
    "premium_customer",
    "enterprise_customer",
    "inactive_sim",
    "expired_subscription",
    "alarm_raised",
    "network_failure",
    "billing_error",
]


@pytest.mark.parametrize("scenario_name", _ALL_SCENARIOS)
def test_every_scenario_builds_with_description_and_entities(scenario_name: str) -> None:
    scenario = getattr(ScenarioLibrary, scenario_name)()
    assert scenario.name == scenario_name
    assert scenario.description
    assert scenario.entities
    assert scenario.all_entities()


def test_roaming_subscriber_referential_consistency() -> None:
    scenario = ScenarioLibrary.roaming_subscriber()
    tenant = scenario.get("tenant")
    subscriber = scenario.get("subscriber")
    network = scenario.get("network")
    zone = scenario.get("zone")
    sim = scenario.get("sim")

    assert subscriber.tenant_id == tenant.tenant_id
    assert network.tenant_id == tenant.tenant_id
    assert zone.tenant_id == tenant.tenant_id
    assert zone.network_id == network.network_id
    assert sim.subscriber_id == subscriber.subscriber_id


def test_enterprise_customer_line_count_is_configurable() -> None:
    scenario = ScenarioLibrary.enterprise_customer(line_count=7)
    subscribers = scenario.get("subscribers")
    assert len(subscribers) == 7
    tenant = scenario.get("tenant")
    assert all(s.tenant_id == tenant.tenant_id for s in subscribers)


def test_blocked_subscriber_scenario_status() -> None:
    scenario = ScenarioLibrary.blocked_subscriber()
    assert scenario.get("subscriber").status == "BLOCKED"


def test_expired_subscription_has_overdue_billing() -> None:
    scenario = ScenarioLibrary.expired_subscription()
    assert scenario.get("subscriber").status == "EXPIRED"
    assert scenario.get("billing").status == "OVERDUE"


def test_alarm_raised_alarm_targets_the_zone() -> None:
    scenario = ScenarioLibrary.alarm_raised()
    zone = scenario.get("zone")
    alarm = scenario.get("alarm")
    assert alarm.entity_type == "STEERING_ZONE"
    assert alarm.entity_id == zone.zone_id
    assert zone.has_leakage is True


def test_network_failure_alarm_targets_the_network() -> None:
    scenario = ScenarioLibrary.network_failure()
    network = scenario.get("network")
    alarm = scenario.get("alarm")
    assert network.status == "DEGRADED"
    assert alarm.entity_id == network.network_id


def test_scenario_get_raises_for_unknown_entity() -> None:
    scenario = ScenarioLibrary.new_subscriber()
    with pytest.raises(KeyError):
        scenario.get("does_not_exist")
