from __future__ import annotations

from datetime import UTC, datetime

from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.builders.models import SimCard
from framework.testdata.generators.telecom_generator import TelecomIdentifierGenerator


class SIMBuilder(BaseBuilder[SimCard]):
    """Fluent builder for `SimCard`."""

    def with_iccid(self, iccid: str) -> SIMBuilder:
        return self._set(iccid=iccid)

    def with_imsi(self, imsi: str) -> SIMBuilder:
        return self._set(imsi=imsi)

    def with_msisdn(self, msisdn: str) -> SIMBuilder:
        return self._set(msisdn=msisdn)

    def with_status(self, status: str) -> SIMBuilder:
        return self._set(status=status)

    def with_subscriber_id(self, subscriber_id: str) -> SIMBuilder:
        return self._set(subscriber_id=subscriber_id)

    def with_tenant_id(self, tenant_id: str) -> SIMBuilder:
        return self._set(tenant_id=tenant_id)

    def active(self) -> SIMBuilder:
        return self._set(status="ACTIVE", activation_date=datetime.now(UTC).isoformat())

    def inactive(self) -> SIMBuilder:
        return self._set(status="INACTIVE", activation_date=None)

    def blocked(self) -> SIMBuilder:
        return self.with_status("BLOCKED")

    def build(self) -> SimCard:
        return SimCard(
            iccid=self._get("iccid", TelecomIdentifierGenerator.iccid),
            imsi=self._get("imsi", TelecomIdentifierGenerator.imsi),
            msisdn=self._get("msisdn", TelecomIdentifierGenerator.msisdn),
            status=self._get("status", lambda: "ACTIVE"),
            subscriber_id=self._get("subscriber_id", lambda: "SUBSCRIBER-1"),
            tenant_id=self._get("tenant_id", lambda: "TENANT-1"),
            activation_date=self._get("activation_date", lambda: datetime.now(UTC).isoformat()),
        )
