from __future__ import annotations

from framework.testdata.builders import AlarmBuilder, BillingBuilder, SIMBuilder
from framework.testdata.factories import (
    AlarmFactory,
    NetworkFactory,
    SteeringRuleFactory,
    SubscriberFactory,
    TenantFactory,
)
from framework.testdata.scenarios.scenario import Scenario


class ScenarioLibrary:
    """Ten reusable, named business scenarios composed from the builders/
    factories — each bundles a coherent, referentially-consistent set of
    entities (a subscriber's `tenant_id` always matches its tenant's
    `tenant_id`, etc.) so the same `Scenario` object can seed a database,
    drive a UI form, and be posted to an API unmodified. See
    docs/ScenarioLibrary.md for the full narrative behind each one.
    """

    @staticmethod
    def new_subscriber() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id)
        subscriber = SubscriberFactory.new(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        return Scenario(
            name="new_subscriber",
            description="A freshly onboarded, active subscriber with no history.",
            entities={"tenant": tenant, "network": network, "subscriber": subscriber},
            tags=("subscriber", "onboarding"),
        )

    @staticmethod
    def roaming_subscriber() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.in_region("EMEA", tenant_id=tenant.tenant_id)
        subscriber = SubscriberFactory.active(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        zone = SteeringRuleFactory.normal(tenant_id=tenant.tenant_id, network_id=network.network_id)
        sim = (
            SIMBuilder()
            .active()
            .with_subscriber_id(subscriber.subscriber_id)
            .with_tenant_id(tenant.tenant_id)
            .build()
        )
        return Scenario(
            name="roaming_subscriber",
            description="An active subscriber currently roaming in a steered zone.",
            entities={
                "tenant": tenant,
                "network": network,
                "subscriber": subscriber,
                "zone": zone,
                "sim": sim,
            },
            tags=("subscriber", "roaming", "steering"),
        )

    @staticmethod
    def blocked_subscriber() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id)
        subscriber = SubscriberFactory.blocked(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        return Scenario(
            name="blocked_subscriber",
            description="A subscriber whose line has been blocked.",
            entities={"tenant": tenant, "network": network, "subscriber": subscriber},
            tags=("subscriber", "blocked"),
        )

    @staticmethod
    def premium_customer() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id)
        subscriber = SubscriberFactory.premium(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        billing = (
            BillingBuilder()
            .paid()
            .with_subscriber_id(subscriber.subscriber_id)
            .with_tenant_id(tenant.tenant_id)
            .with_amount(199.99)
            .build()
        )
        return Scenario(
            name="premium_customer",
            description="A Gold-tier subscriber with an up-to-date, paid premium plan.",
            entities={
                "tenant": tenant,
                "network": network,
                "subscriber": subscriber,
                "billing": billing,
            },
            tags=("subscriber", "premium", "billing"),
        )

    @staticmethod
    def enterprise_customer(*, line_count: int = 5) -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id)
        subscribers = [
            SubscriberFactory.active(tenant_id=tenant.tenant_id, network_id=network.network_id)
            for _ in range(line_count)
        ]
        return Scenario(
            name="enterprise_customer",
            description=f"A tenant with {line_count} active subscriber lines under one account.",
            entities={"tenant": tenant, "network": network, "subscribers": subscribers},
            tags=("tenant", "enterprise"),
        )

    @staticmethod
    def inactive_sim() -> Scenario:
        tenant = TenantFactory.active()
        subscriber = SubscriberFactory.active(tenant_id=tenant.tenant_id)
        sim = (
            SIMBuilder()
            .inactive()
            .with_subscriber_id(subscriber.subscriber_id)
            .with_tenant_id(tenant.tenant_id)
            .build()
        )
        return Scenario(
            name="inactive_sim",
            description="An active subscriber whose SIM has not been activated.",
            entities={"tenant": tenant, "subscriber": subscriber, "sim": sim},
            tags=("subscriber", "sim"),
        )

    @staticmethod
    def expired_subscription() -> Scenario:
        tenant = TenantFactory.active()
        subscriber = SubscriberFactory.active(tenant_id=tenant.tenant_id, status="EXPIRED")
        billing = (
            BillingBuilder()
            .overdue()
            .with_subscriber_id(subscriber.subscriber_id)
            .with_tenant_id(tenant.tenant_id)
            .with_description("Subscription renewal overdue")
            .build()
        )
        return Scenario(
            name="expired_subscription",
            description="A subscriber whose subscription period has lapsed, with an overdue bill.",
            entities={"tenant": tenant, "subscriber": subscriber, "billing": billing},
            tags=("subscriber", "billing", "expired"),
        )

    @staticmethod
    def alarm_raised() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id)
        zone = SteeringRuleFactory.with_leakage(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        alarm = (
            AlarmBuilder()
            .critical()
            .active()
            .with_entity("STEERING_ZONE", zone.zone_id)
            .with_description("Leakage threshold exceeded")
            .build()
        )
        return Scenario(
            name="alarm_raised",
            description="A critical alarm raised against a steering zone with traffic leakage.",
            entities={"tenant": tenant, "network": network, "zone": zone, "alarm": alarm},
            tags=("alarm", "steering"),
        )

    @staticmethod
    def network_failure() -> Scenario:
        tenant = TenantFactory.active()
        network = NetworkFactory.active(tenant_id=tenant.tenant_id, status="DEGRADED")
        zone = SteeringRuleFactory.network_failure(
            tenant_id=tenant.tenant_id, network_id=network.network_id
        )
        alarm = AlarmFactory.network_failure(network.network_id)
        return Scenario(
            name="network_failure",
            description="A network reporting degraded status with a corresponding critical alarm.",
            entities={"tenant": tenant, "network": network, "zone": zone, "alarm": alarm},
            tags=("network", "alarm", "outage"),
        )

    @staticmethod
    def billing_error() -> Scenario:
        tenant = TenantFactory.active()
        subscriber = SubscriberFactory.active(tenant_id=tenant.tenant_id)
        billing = (
            BillingBuilder()
            .billing_error()
            .with_subscriber_id(subscriber.subscriber_id)
            .with_tenant_id(tenant.tenant_id)
            .build()
        )
        return Scenario(
            name="billing_error",
            description="A subscriber whose latest billing run failed to process.",
            entities={"tenant": tenant, "subscriber": subscriber, "billing": billing},
            tags=("subscriber", "billing", "error"),
        )
