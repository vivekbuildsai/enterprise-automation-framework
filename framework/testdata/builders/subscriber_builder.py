from __future__ import annotations

from datetime import UTC, datetime

from framework.database.models import Subscriber
from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.generators.telecom_generator import TelecomIdentifierGenerator
from framework.testdata.utilities.id_sequence import sequences

_subscriber_sequence = sequences.get("subscriber")

_COS_TIERS = ("Gold", "Silver", "Bronze")


class SubscriberBuilder(BaseBuilder[Subscriber]):
    """Fluent builder for `framework.database.models.Subscriber`. MSISDN/
    IMSI default to `TelecomIdentifierGenerator` (structurally valid, not
    real-world allocated numbers) rather than plain random digits.
    """

    def with_subscriber_id(self, subscriber_id: str) -> SubscriberBuilder:
        return self._set(subscriber_id=subscriber_id)

    def with_msisdn(self, msisdn: str) -> SubscriberBuilder:
        return self._set(msisdn=msisdn)

    def with_imsi(self, imsi: str) -> SubscriberBuilder:
        return self._set(imsi=imsi)

    def with_status(self, status: str) -> SubscriberBuilder:
        return self._set(status=status)

    def with_cos(self, cos: str) -> SubscriberBuilder:
        return self._set(cos=cos)

    def with_tenant_id(self, tenant_id: str) -> SubscriberBuilder:
        return self._set(tenant_id=tenant_id)

    def with_network_id(self, network_id: str) -> SubscriberBuilder:
        return self._set(network_id=network_id)

    def with_created_at(self, created_at: str) -> SubscriberBuilder:
        return self._set(created_at=created_at)

    def with_updated_at(self, updated_at: str) -> SubscriberBuilder:
        return self._set(updated_at=updated_at)

    def active(self) -> SubscriberBuilder:
        return self.with_status("ACTIVE")

    def suspended(self) -> SubscriberBuilder:
        return self.with_status("SUSPENDED")

    def blocked(self) -> SubscriberBuilder:
        return self.with_status("BLOCKED")

    def gold_tier(self) -> SubscriberBuilder:
        return self.with_cos("Gold")

    def build(self) -> Subscriber:
        now = datetime.now(UTC).isoformat()
        return Subscriber(
            subscriber_id=self._get(
                "subscriber_id", lambda: _subscriber_sequence.next_id(prefix="SUBSCRIBER")
            ),
            msisdn=self._get("msisdn", TelecomIdentifierGenerator.msisdn),
            imsi=self._get("imsi", TelecomIdentifierGenerator.imsi),
            status=self._get("status", lambda: "ACTIVE"),
            cos=self._get("cos", lambda: _COS_TIERS[0]),
            tenant_id=self._get("tenant_id", lambda: "TENANT-1"),
            network_id=self._get("network_id", lambda: "NETWORK-1"),
            created_at=self._get("created_at", lambda: now),
            updated_at=self._get("updated_at", lambda: now),
        )
