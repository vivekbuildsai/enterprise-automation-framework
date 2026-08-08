from __future__ import annotations

from typing import Any

from framework.testdata.builders import BillingBuilder
from framework.testdata.builders.models import BillingRecord


class BillingFactory:
    @staticmethod
    def paid(**overrides: Any) -> BillingRecord:
        return BillingBuilder().paid().with_fields(**overrides).build()

    @staticmethod
    def overdue(**overrides: Any) -> BillingRecord:
        return BillingBuilder().overdue().with_fields(**overrides).build()

    @staticmethod
    def error(**overrides: Any) -> BillingRecord:
        return BillingBuilder().billing_error().with_fields(**overrides).build()
