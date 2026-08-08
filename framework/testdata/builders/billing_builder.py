from __future__ import annotations

from datetime import UTC, datetime

from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.builders.models import BillingRecord
from framework.testdata.utilities.id_sequence import sequences
from framework.utilities.random_data import RandomData

_billing_sequence = sequences.get("billing")


class BillingBuilder(BaseBuilder[BillingRecord]):
    """Fluent builder for `BillingRecord`."""

    def with_billing_id(self, billing_id: str) -> BillingBuilder:
        return self._set(billing_id=billing_id)

    def with_subscriber_id(self, subscriber_id: str) -> BillingBuilder:
        return self._set(subscriber_id=subscriber_id)

    def with_tenant_id(self, tenant_id: str) -> BillingBuilder:
        return self._set(tenant_id=tenant_id)

    def with_amount(self, amount: float, *, currency: str = "USD") -> BillingBuilder:
        return self._set(amount=amount, currency=currency)

    def with_billing_date(self, billing_date: str) -> BillingBuilder:
        return self._set(billing_date=billing_date)

    def with_status(self, status: str) -> BillingBuilder:
        return self._set(status=status)

    def with_description(self, description: str) -> BillingBuilder:
        return self._set(description=description)

    def paid(self) -> BillingBuilder:
        return self.with_status("PAID")

    def overdue(self) -> BillingBuilder:
        return self.with_status("OVERDUE")

    def billing_error(self) -> BillingBuilder:
        return self._set(status="ERROR", description="Billing processing failed")

    def build(self) -> BillingRecord:
        return BillingRecord(
            billing_id=self._get("billing_id", lambda: _billing_sequence.next_id(prefix="BILL")),
            subscriber_id=self._get("subscriber_id", lambda: "SUBSCRIBER-1"),
            tenant_id=self._get("tenant_id", lambda: "TENANT-1"),
            amount=self._get("amount", lambda: round(RandomData.random_int(500, 20000) / 100, 2)),
            currency=self._get("currency", lambda: "USD"),
            billing_date=self._get("billing_date", lambda: datetime.now(UTC).isoformat()),
            status=self._get("status", lambda: "PAID"),
            description=self._get("description", lambda: "Monthly subscription charge"),
        )
