from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from framework.database.exceptions import SeedDataError
from framework.database.models import Network, SteeringZone, Subscriber, Tenant
from framework.database.repositories import (
    NetworkRepository,
    SteeringRepository,
    SubscriberRepository,
    TenantRepository,
)
from framework.database.utilities.query_executor import QueryExecutor
from framework.utilities.random_data import RandomData


@dataclass(frozen=True, slots=True)
class SeedResult:
    tenant: Tenant
    network: Network
    subscribers: list[Subscriber]
    zones: list[SteeringZone]


class SeedManager:
    """Populates the demo schema with a small, deterministic-*shaped* (fixed
    field count/relationships, randomized values via `RandomData`) baseline
    dataset — enough for repository/validator/hybrid tests to have real rows
    to query without every test hand-writing its own fixture data.

    Reuses `framework.utilities.RandomData` (the same Faker wrapper the UI
    test-data layer uses) rather than a second random-data implementation.
    """

    def __init__(self, executor: QueryExecutor) -> None:
        self._executor = executor
        self._tenants = TenantRepository(executor)
        self._networks = NetworkRepository(executor)
        self._subscribers = SubscriberRepository(executor)
        self._zones = SteeringRepository(executor)

    def seed_baseline(
        self, *, tenant_id: str = "T-BASE", network_id: str = "N-BASE", subscriber_count: int = 3
    ) -> SeedResult:
        try:
            now = datetime.now(UTC).isoformat()

            tenant = Tenant(
                tenant_id=tenant_id,
                tenant_code="A01",
                tenant_name="Baseline Tenant",
                status="ACTIVE",
                created_at=now,
            )
            self._tenants.create(tenant)

            network = Network(
                network_id=network_id,
                network_code="N1",
                network_name="Baseline Network",
                tenant_id=tenant_id,
                ota_region="EMEA",
                status="ACTIVE",
            )
            self._networks.create(network)

            subscribers = []
            for i in range(subscriber_count):
                subscriber = Subscriber(
                    subscriber_id=f"{tenant_id}-SUB-{i}",
                    msisdn=f"4477{RandomData.random_int(10000000, 99999999)}",
                    imsi=f"234{RandomData.random_int(1000000000, 9999999999)}",
                    status="ACTIVE",
                    cos="Gold" if i % 2 == 0 else "Silver",
                    tenant_id=tenant_id,
                    network_id=network_id,
                    created_at=now,
                    updated_at=now,
                )
                self._subscribers.create(subscriber)
                subscribers.append(subscriber)

            # Fixed leakage/anti-SoR combination per zone (not randomized) so
            # tests asserting "N zones have leakage" stay deterministic.
            zone_specs = [("LBTR", 1, 0), ("SRDC", 0, 1), ("LBTR", 0, 0)]
            zones = []
            for i, (tr_type, leakage_flag, anti_sor_flag) in enumerate(zone_specs):
                zone = SteeringZone(
                    zone_id=f"{tenant_id}-ZONE-{i}",
                    zone_code=f"Country_{tenant_id}_{i}",
                    country=f"Country_{i}",
                    tenant_id=tenant_id,
                    network_id=network_id,
                    tr_type=tr_type,
                    cos="Gold",
                    ota_region="EMEA",
                    roamer_count=RandomData.random_int(10, 500),
                    data_usage_mb=RandomData.random_int(100, 9000),
                    leakage_flag=leakage_flag,
                    anti_sor_flag=anti_sor_flag,
                    status="ACTIVE",
                    modified_by="Admin",
                    modified_date=now,
                )
                self._zones.create(zone)
                zones.append(zone)

            return SeedResult(tenant=tenant, network=network, subscribers=subscribers, zones=zones)
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain-specific error
            raise SeedDataError(f"Failed to seed baseline dataset: {exc}") from exc
