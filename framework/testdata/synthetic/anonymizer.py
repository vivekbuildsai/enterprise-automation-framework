from __future__ import annotations

from collections.abc import Callable
from typing import Any

from framework.testdata.generators.telecom_generator import TelecomIdentifierGenerator
from framework.testdata.masking.pii_fields import PII_FIELDS
from framework.utilities.random_data import RandomData

_GENERATORS: dict[str, Callable[[], Any]] = {
    "email": RandomData.email,
    "first_name": lambda: RandomData.full_name().split()[0],
    "last_name": lambda: RandomData.full_name().split()[-1],
    "username": RandomData.username,
    "full_address": RandomData.full_address,
    "street_address": RandomData.street_address,
    "date_of_birth": lambda: RandomData.date_of_birth().isoformat(),
    "msisdn": TelecomIdentifierGenerator.msisdn,
    "imsi": TelecomIdentifierGenerator.imsi,
    "iccid": TelecomIdentifierGenerator.iccid,
}


class Anonymizer:
    """Replaces PII fields in a real-shaped record with freshly-generated
    synthetic equivalents — for teams that need production-*like* data
    (real record structure, realistic-looking values) without any real
    subscriber's actual PII surviving into a test environment. Pairs with
    `DataMasker` (which obscures a value in place) but produces a still
    *usable* synthetic value instead of a redacted, unusable one.
    """

    @staticmethod
    def anonymize(
        record: dict[str, Any], *, fields: frozenset[str] | set[str] | None = None
    ) -> dict[str, Any]:
        target_fields = fields if fields is not None else PII_FIELDS
        anonymized = dict(record)
        for field in target_fields:
            if field in anonymized and field in _GENERATORS:
                anonymized[field] = _GENERATORS[field]()
        return anonymized
